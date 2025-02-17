import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import logging
import time

from order_book.product_manager import TradingProductManager
from src.order_book.order import Order
from src.protocols.FIXProtocol import FIXProtocol

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger("tornado.access").disabled = True

config = json.load(open("config/server_config.json"))
MSG_SEQ_NUM = 0
ID = 0

# Initialize order books and matching engines for multiple products
products = ["product1", "product2", "product3"]  # Add more products as needed

product_manager = TradingProductManager(products)
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
        message = json.loads(self.request.body)
        logging.info(f"R> {message['message']}")
        msg_type = message["msg_type"]

        handler = self.msg_type_handlers.get(msg_type) # Call appropriate handler
        if not handler:
            self.set_status(400)
            self.write({"error": f"Unknown message type: {msg_type}"})
            return

        response = handler(message)
        logging.debug(f"S> {response}")
        self.write({"message": response.decode()})


class TradingHandler(MsgHandler):
    @staticmethod
    def match_order(message):
        """
        Tries to match an order with the existing orders in the order book,
        remaining quantity is added to the order book.
        :param message: client message with order details (user, side, quantity, price)
        :return: server response
        """
        global ID
        message = protocol.decode(message)
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReport"})
        order = Order(
            str(ID),  # Order ID
            time.time_ns(),  # Timestamp in nanoseconds
            message["order"]["user"],
            message["order"]["side"],
            message["order"]["quantity"],
            message["order"]["price"]
        )
        ID += 1  # Increment order ID
        status = product_manager.get_matching_engine(product).match_order(order) # Match order
        protocol.set_target(message["order"]["user"])  # Set target to user
        return protocol.encode({"order_id": order.id, "status": status, "msg_type": "ExecutionReport"})

    @staticmethod
    def delete_order(message):
        """
        Deletes an order from the order book.
        :param message: client message with order ID
        :return: server response
        """
        message = protocol.decode(message)
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReportCancel"})
        order_id = message["order_id"]
        order = product_manager.get_order_book(product).get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportCancel"})
        product_manager.get_order_book(product).delete_order(order_id)
        protocol.set_target(order.user)
        return protocol.encode({"order_id": order_id, "status": True, "msg_type": "ExecutionReportCancel"})

    @staticmethod
    def modify_order_qty(message):
        """
        Modifies an order's quantity - only decrease is allowed.
        :param message: client message with order ID and new quantity
        :return: server response
        """
        message = protocol.decode(message)
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_id": -1, "status": False, "msg_type": "ExecutionReportModify"})
        order_id = message["order_id"]
        quantity = message["quantity"]
        order = product_manager.get_order_book(product).get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportModify"})
        ret = product_manager.get_order_book(product).modify_order_qty(order_id, quantity)
        protocol.set_target(order.user)
        return protocol.encode({"order_id": order_id, "status": ret, "msg_type": "ExecutionReportModify"})

    msg_type_handlers = {
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
        message = protocol.decode(message)
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order": None, "msg_type": "OrderStatus"})
        order_book = product_manager.get_order_book(product)
        order_id = message["id"]
        order = order_book.get_order_by_id(order_id)
        protocol.set_target(message["sender"])
        return protocol.encode({"order": order, "msg_type": "OrderStatus"})

    @staticmethod
    def order_book_request(message):
        """
        Returns the order book.
        :param message: client message with product name
        :return: server response
        """
        message = protocol.decode(message)
        product = message["product"]
        if not product_exists(product):
            return protocol.encode({"order_book": None, "msg_type": "MarketDataSnapshot"})
        order_book = product_manager.get_order_book(product)
        order_book_data = order_book.jsonify_order_book()
        return protocol.encode({"order_book": order_book_data, "msg_type": "MarketDataSnapshot"})

    @staticmethod
    def user_data(message):
        """
        Returns the orders of a user.
        :param message: client message with user ID
        :return: server response
        """
        message = protocol.decode(message)
        product = message["product"]
        print(product_manager.get_order_book(product).user_balance)
        if not product_exists(product):
            return protocol.encode({"user_orders": None, "msg_type": "UserOrderStatus"})
        order_book = product_manager.get_order_book(product)
        user_orders = order_book.get_orders_by_user(message["user"])
        user_orders = {order.id: order.__json__() for order in user_orders}
        protocol.set_target(message["user"])
        return protocol.encode({"user_orders": user_orders, "msg_type": "UserOrderStatus"})

    msg_type_handlers = {
        "OrderStatusRequest": lambda message: QuoteHandler.order_stats(message),
        "MarketDataRequest": lambda message: QuoteHandler.order_book_request(message),
        "UserOrderStatusRequest": lambda message: QuoteHandler.user_data(message)
    }

    def get(self):
        """
        Handles GET requests from the client.
        :return: None
        """
        self.handle_msg()


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (f"/{config['TRADING_SESSION']}", TradingHandler),
        (f"/{config['QUOTE_SESSION']}", QuoteHandler),
    ], debug=True, autoreload=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(config["PORT"], address=config["HOST"].replace("http://", ""))
    print(f"Server started on {config['HOST']}:{config['PORT']}")
    tornado.ioloop.IOLoop.current().start()
