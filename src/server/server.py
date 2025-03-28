import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

import traceback
import atexit
import pickle
import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import logging
import colorlog
import time
import uuid

from src.order_book.product_manager import TradingProductManager
from src.server.user_manager import UserManager
from src.order_book.order import Order
from src.protocols.FIXProtocol import FIXProtocol

# Configure logging to use colorlog
handler = logging.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
))
logging.basicConfig(level=logging.ERROR, handlers=[handler])
logging.getLogger("tornado.access").disabled = True

config = json.load(open("../config/server_config.json"))
MSG_SEQ_NUM = 0
ID = 0

# Initialize order books and matching engines for multiple products
products = ["product1", "product2"]  # Add more products as needed
products = ["product1"]  # Add more products as needed

# Trading fees, values taken from https://www.investopedia.com/terms/b/brokerage-fee.asp
fixed_fee=0.01
percentage_fee=0.001
per_share_fee=0.005

product_manager = TradingProductManager(products)
user_manager = UserManager()
protocol = FIXProtocol("server")


def product_exists(product):
    """
    Check if the product is valid.
    :param product: Product name
    :return: True if valid, False otherwise
    """
    return product in products


class MainHandler(tornado.web.RequestHandler):
    """
    Main handler for the web server.
    """

    def get(self):
        self.write("This is the trading server")


class MsgHandler(tornado.web.RequestHandler):
    """
    A base handler class that provides the common message handling functionality.
    Subclasses must define `msg_type_handlers`.
    """

    msg_type_handlers = {}  # Must be overridden in subclasses

    def handle_msg(self):
        """
        Handles requests from the client.
        :return: None
        """
        try:
            message = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"error": "Invalid JSON format"})
            return
        logging.info(f"R> {message['message']}")
        msg_type = message["msg_type"]

        handler = self.msg_type_handlers.get(msg_type)  # Call appropriate handler
        if not handler:
            self.set_status(400)
            self.write({"error": f"Unknown message type: {msg_type}"})
            return
        try:
            message = protocol.decode(message)
            user_ID = message["user"]
            if not user_manager.user_exists(user_ID) and msg_type != "RegisterRequest":
                self.set_status(400)
                self.write({"error": "Invalid user ID, please register first"})
                return
            response = handler(message)
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
            self.set_status(500)
            self.write({"error": f"Error in handling message: {e}"})
            logging.error(f"Error in handling message: {e}")
            return
        logging.debug(f"S> {response}")
        self.write({"message": response.decode()})
    @staticmethod
    def update_user_post_buy_budget(user_ID):
        """
        Update the user's post-buy budget.
        :param user_ID: User ID
        """
        initial_budget = user_manager.users[user_ID].budget
        balance = sum(product_manager.get_order_book(product, False)
                      .user_balance[user_ID]["balance"] for product in products)

        # Get all buy orders of the user and update the post-buy budget
        buy_orders_value = sum(order.price * order.quantity for product in products
                               if (order_book := product_manager.get_order_book(product, False))
                               for order in order_book.get_orders_by_user(user_ID) if order.side == "buy")
        user_manager.users[user_ID].post_buy_budget = initial_budget - buy_orders_value + balance

    @staticmethod
    def update_user_post_sell_volume(user_ID, product):
        """
        Update the user's post-buy budget.
        :param user_ID: User ID
        :param product: Product name
        """
        volume = product_manager.get_order_book(product, False).user_balance[user_ID]["volume"]
        # Get all sell orders of the user and update the post-sell volume
        sell_orders_volume = sum(order.quantity for order in product_manager.get_order_book(product, False)
                                 .get_orders_by_user(user_ID) if order.side == "sell")
        product_manager.get_order_book(product, False).user_balance[user_ID]["post_sell_volume"] = volume - sell_orders_volume

class TradingHandler(MsgHandler):
    @staticmethod
    def register(message):
        """
        Registers a new user.
        :param message: client message with user budget
        :return: unique user ID
        """
        user_ID = str(uuid.uuid4())
        user_manager.add_user(message["user"], user_ID, message["budget"])
        return protocol.encode({"user": user_ID, "msg_type": "RegisterResponse"})  # Return user ID

    @staticmethod
    def initialize_liq_engine(message):
        """
        Initializes the liquidity engine.
        :param message: client message with user budget
        :return: unique user ID
        """
        user = message["user"]
        budget = message["budget"]
        volume = message["volume"]
        for product in products:
            order_book = product_manager.get_order_book(product, False)
            order_book.modify_user_balance(user, 0, volume[product] if isinstance(volume, dict) else volume)
            user_manager.set_user_budget(user, budget)
        user_balance = {product: product_manager.get_order_book(product, False).user_balance[user] for product in products}
        return protocol.encode({"user_balance": user_balance, "msg_type": "UserBalance"})

    @staticmethod
    def match_order(message):
        """
        Tries to match an order with the existing orders in the order book,
        remaining quantity is added to the order book.
        :param message: client message with order details (user, side, quantity, price)
        :return: server response
        """
        global ID
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})

        # Check order details viability
        if message["order"]["side"] not in ["buy", "sell"]:
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})
        if message["order"]["quantity"] <= 0 or message["order"]["price"] <= 0:
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})

        # If the order is a buy order, check if the user has enough budget to place the order
        if message["order"]["side"] == "buy":
            TradingHandler.update_user_post_buy_budget(message["order"]["user"])
            if user_manager.users[message["order"]["user"]].post_buy_budget < message["order"]["quantity"] * message["order"]["price"]:
                return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})

        # If the order is a sell order, check if the user has enough shares to sell
        if message["order"]["side"] == "sell":
            TradingHandler.update_user_post_sell_volume(message["order"]["user"], product)
            user_shares = product_manager.get_order_book(product, False).user_balance[message["user"]]["post_sell_volume"]
            if user_shares < message["order"]["quantity"]:
                return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})

        timestamp = time.time_ns()
        order = Order(
            str(ID),  # Order ID
            timestamp,  # Timestamp in nanoseconds
            message["order"]["user"],
            message["order"]["side"],
            message["order"]["quantity"],
            message["order"]["price"]
        )
        ID += 1  # Increment order ID
        status = product_manager.get_matching_engine(product, timestamp).match_order(order)  # Match order
        protocol.set_target(message["order"]["user"])  # Set target to user
        response = protocol.encode({"order_id": order.id, "status": status, "msg_type": "ExecutionReport"})
        if status is not False: # If the order was added to the order book or fully matched -> apply trading fee
            percentage_based_fee = order.price * percentage_fee
            per_share_based_fee = order.quantity * per_share_fee
            total_fee = fixed_fee + percentage_based_fee + per_share_based_fee
            user_manager.users[message["order"]["user"]].budget -= total_fee

        # Broadcast the order book to all clients
        broadcast_response = protocol.encode(
            {"order_book": product_manager.get_order_book(product, False).jsonify_order_book(),
             "product": product, "msg_type": "MarketDataSnapshot"})
        WebSocketHandler.broadcast(broadcast_response)
        return response

    @staticmethod
    def delete_order(message):
        """
        Deletes an order from the order book.
        :param message: client message with order ID
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReportCancel"})
        order_id = message["order_id"]
        order = product_manager.get_order_book(product, False).get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportCancel"})
        if order.user != message["user"]: # Check if the user is the owner of the order
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportCancel"})
        product_manager.get_order_book(product, timestamp=time.time_ns()).delete_order(order_id)
        protocol.set_target(order.user)

        # Broadcast the order book to all clients
        broadcast_response = protocol.encode(
            {"order_book": product_manager.get_order_book(product, False).jsonify_order_book(),
             "product": product, "msg_type": "MarketDataSnapshot"})
        WebSocketHandler.broadcast(broadcast_response)
        return protocol.encode({"order_id": order_id, "status": True, "msg_type": "ExecutionReportCancel"})

    @staticmethod
    def modify_order_qty(message):
        """
        Modifies an order's quantity - only decrease is allowed.
        :param message: client message with order ID and new quantity
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReportModify"})
        order_id = message["order_id"]
        quantity = message["quantity"]
        order = product_manager.get_order_book(product, False).get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportModify"})
        ret = product_manager.get_order_book(product, time.time_ns()).modify_order_qty(order_id, quantity)
        protocol.set_target(order.user)
        return protocol.encode({"order_id": order_id, "status": ret, "msg_type": "ExecutionReportModify"})

    msg_type_handlers = {
        "RegisterRequest": lambda message: TradingHandler.register(message),
        "InitializeLiquidityEngine": lambda message: TradingHandler.initialize_liq_engine(message),
        "NewOrderSingle": lambda message: TradingHandler.match_order(message),
        "OrderCancelRequest": lambda message: TradingHandler.delete_order(message),
        "OrderModifyRequestQty": lambda message: TradingHandler.modify_order_qty(message)
    }

    def post(self):
        """
        Handles POST requests from the client.
        :return: None
        """
        self.handle_msg()


class QuoteHandler(MsgHandler):
    @staticmethod
    def order_stats(message):
        """
        Returns the status of an order.
        :param message: client message with order ID
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order": None, "msg_type": "OrderStatus"})
        order_book = product_manager.get_order_book(product, False)
        order_id = message["id"]
        order = order_book.get_order_by_id(order_id)
        protocol.set_target(message["user"])
        return protocol.encode({"order": order, "msg_type": "OrderStatus"})

    @staticmethod
    def order_book_request(message):
        """
        Returns the order book.
        :param message: client message with product name
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_book": None, "product": product, "msg_type": "MarketDataSnapshot"})
        order_book = product_manager.get_order_book(product, False)
        order_book_data = order_book.jsonify_order_book()
        return protocol.encode({"order_book": order_book_data, "product": product, "msg_type": "MarketDataSnapshot"})

    @staticmethod
    def user_data(message):
        """
        Returns the orders of a user.
        :param message: client message with user ID
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"user_orders": None, "msg_type": "UserOrderStatus"})
        order_book = product_manager.get_order_book(product, False)
        user_orders = order_book.get_orders_by_user(message["user"])
        user_orders = {order.id: order.__json__() for order in user_orders}
        protocol.set_target(message["user"])
        return protocol.encode({"user_orders": user_orders, "msg_type": "UserOrderStatus"})

    @classmethod
    def user_balance(cls, message):
        """
        Returns records of the balance of a user.
        :param message: client message with user ID
        :return: server response
        """
        cls.update_user_post_buy_budget(message["user"])
        cls.update_user_post_sell_volume(message["user"], message["product"])
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"user_balance": None, "msg_type": "UserBalance"})
        historical_books = product_manager.historical_order_books[product]
        user_balances = [
            {**book_data["UserBalance"][message["user"]], 'timestamp': book_data['Timestamp']}
            for book in historical_books
            if (book_data := json.loads(book)) and message["user"] in book_data["UserBalance"]
        ]
        # Add current balance
        user_balances.append(product_manager.get_order_book(product, False).user_balance[message["user"]])
        # user_balances[-1]['timestamp'] = time.time_ns()
        protocol.set_target(message["user"])
        user_balances = {"history_balance": user_balances, "current_balance": user_balances[-1],
                         "budget": user_manager.users[message["user"]].budget,
                         "post_buy_budget": user_manager.users[message["user"]].post_buy_budget}
        return protocol.encode({"user_balance": user_balances, "msg_type": "UserBalance"})

    @staticmethod
    def get_report(message):
        """
        Returns the historical report of the trading session.
        :param message: client message with product name
        :return: server response
        """
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"report": None, "msg_type": "CaptureReport"})
        report = product_manager.get_historical_order_books(product, message["history_len"])
        # Add current order book to the historical report
        report.append(product_manager.get_order_book(product, False).copy().jsonify_order_book())
        return protocol.encode({"history": report, "msg_type": "CaptureReport"})

    msg_type_handlers = {
        "OrderStatusRequest": lambda message: QuoteHandler.order_stats(message),
        "MarketDataRequest": lambda message: QuoteHandler.order_book_request(message),
        "UserOrderStatusRequest": lambda message: QuoteHandler.user_data(message),
        "UserBalanceRequest": lambda message: QuoteHandler.user_balance(message),
        "CaptureReportRequest": lambda message: QuoteHandler.get_report(message)
    }

    def get(self):
        """
        Handles GET requests from the client.
        :return: None
        """
        self.handle_msg()


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Websocket handler for message exchange between the server and the client.
    """
    clients = set()

    def open(self):
        """
        Handles new WebSocket connections - adds the client to the subscribed clients.
        """
        self.clients.add(self)
        logging.info("New WebSocket connection")

    def on_close(self):
        """
        Handles WebSocket connection close - removes the client from the subscribed clients.
        """
        self.clients.remove(self)
        logging.info("WebSocket connection closed")

    def on_message(self, message):
        """
        Handles messages from the client.
        """
        # pass
        self.write_message(f">{message}")

    @classmethod
    def broadcast(cls, message):
        """
        Broadcasts a message to all subscribed clients.
        :param message: message to broadcast
        """
        message = {"message": message.decode()}
        for client in cls.clients:
            client.write_message(message)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (f"/{config['TRADING_SESSION']}", TradingHandler),
        (f"/{config['QUOTE_SESSION']}", QuoteHandler),
        (r"/websocket", WebSocketHandler),
    ], debug=True, autoreload=True)

def save_data():
    data_to_save = {}
    for product in products:
        report = product_manager.get_historical_order_books(product, -1)
        report.append(product_manager.get_order_book(product, False).copy().jsonify_order_book())
        data_to_save[product] = {"order_books": report, "users": user_manager.users}
    with open('server_data.pickle', 'wb') as f:
        pickle.dump(data_to_save, f)
    print("Data saved to server_data.pickle")

# Register the save_data function to be called at exit
atexit.register(save_data)

if __name__ == "__main__":
    app = make_app()
    app.listen(config["PORT"])
    print(f"Server started on {config['HOST']}:{config['PORT']}")
    tornado.ioloop.IOLoop.current().start()
