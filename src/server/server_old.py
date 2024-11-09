import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import logging
import time
import simplefix
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
from src.protocols.fix import FIXProtocol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# TODO log outcoming messages as debug

config = json.load(open("config/server_config.json"))
BEGIN_STRING = "8=FIX.4.4"
MSG_SEQ_NUM = 0
ID = 0

order_book = OrderBook()
fifo_matching_engine = FIFOMatchingEngine(order_book)
protocol = FIXProtocol("server")


def make_order(data):
    """
    Create an order object from the FIX message
    :param data: FIX message data
    :return: Order object
    """
    global ID
    timestamp = time.time_ns()
    side = data.get(54)  # 54 = Side
    if side == b'1':
        side = 'buy'
    else:
        side = 'sell'
    order = Order(
        str(ID),
        timestamp,
        data.get(49).decode(),  # user
        side,
        int(data.get(38).decode()),  # quantity
        float(data.get(44).decode())  # price
    )
    ID += 1
    return order

def parse_message(request):
    """
    Parse the incoming FIX message.
    :param request: FIX message
    :return: Decoded message
    """
    parser = simplefix.FixParser()
    data = json.loads(request.body)

    message = data['message']
    parser.append_buffer(message)
    message = parser.get_message()
    logging.info(f"R>: {message}")
    return message

def fix_message_init(TARGET):
    """
    Initialize a FIX message with standard header tags.
    :param TARGET: Target ID
    :return: simplefix.FixMessage object
    """
    global MSG_SEQ_NUM
    message = simplefix.FixMessage()
    message.append_string(BEGIN_STRING, header=True)
    message.append_pair(56, TARGET, header=True)
    message.append_string("49=server", header=True)
    message.append_utc_timestamp(52, precision=6, header=True)
    message.append_pair(34, MSG_SEQ_NUM, header=True)
    MSG_SEQ_NUM += 1
    return message


class MainHandler(tornado.web.RequestHandler):
    """
    Main handler for the web server.
    """
    def get(self):
        self.write("This is the trading server")


class TradeHandler(tornado.web.RequestHandler):
    """
    Handler for trading-related requests.
    """
    # TODO fix message response to client

    def order_stats(self, data):
        order_id = data.get(41).decode()
        order = order_book.get_order_by_id(order_id)
        message = fix_message_init(data.get(49).decode())
        if order:
            order = order.__json__()
            message.append_pair(35, "8")  # OrdStatus = New
            message.append_pair(39, "1")  # OrdStatus = Remaining (partially filled) quantity
            message.append_pair(37, order['id']) # OrderID
            message.append_pair(54, 1 if order['side'] == 'buy' else 2) # Side
            message.append_pair(151, order['quantity']) # LeavesQty
            message.append_pair(44, order['price']) # Price
        else:
            message.append_pair(39, "8")  # OrdStatus = Rejected
        byte_buffer = message.encode()
        self.write({"message": byte_buffer.decode()})

    def match_order(self, data):
        order = make_order(data)
        order_id = order.id
        ret = fifo_matching_engine.match_order(order)
        if ret is None:
            self.write({"message": "Order fully matched", "status": "filled", "order_id": order_id})
        elif ret is True:
            self.write({"message": "Order partially matched", "status": "not filled", "order_id": order_id})
        else:
            self.write({"message": "Order match failed", "status": "failed", "order_id": order_id})

    def delete_order(self, data):
        order_id = data.get(41).decode()
        ret = order_book.delete_order(str(order_id))
        if ret:
            self.write({"message": "Order deleted successfully"})
        else:
            self.write({"message": "Order not found"})

    def modify_order_qty(self, data):
        order_id = data.get(41).decode()
        order_id = str(order_id)
        new_quantity = int(data.get(38).decode())
        ret = order_book.modify_order_qty(order_id, new_quantity)
        if ret:
            self.write({"message": "Order quantity modified successfully"})
        else:
            self.write({"message": "Order quantity modification failed, order not found or quantity increase"})

    msg_type_handlers = {b"D": match_order, b"F": delete_order, b"G": modify_order_qty, b"H": order_stats}

    def post(self):
        message = parse_message(self.request)

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)

    def get(self):
        message = parse_message(self.request)

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)


class QuoteHandler(tornado.web.RequestHandler):

    def order_stats(self, data):
        order_id = data.get(41).decode()
        order = order_book.get_order_by_id(order_id)
        message = fix_message_init(data.get(49).decode())
        if order:
            order = order.__json__()
            message.append_pair(35, "8")  # OrdStatus = New
            message.append_pair(39, "1")  # OrdStatus = Remaining (partially filled) quantity
            message.append_pair(37, order['id']) # OrderID
            message.append_pair(54, 1 if order['side'] == 'buy' else 2) # Side
            message.append_pair(151, order['quantity']) # LeavesQty
            message.append_pair(44, order['price']) # Price
        else:
            message.append_pair(39, "8")  # OrdStatus = Rejected
        byte_buffer = message.encode()
        self.write({"message": byte_buffer.decode()})

    def market_data(self, data):
        order_book_data = order_book.jsonify_order_book()
        self.write(order_book_data)

    def user_data(self, data):
        user = data.get(49).decode()
        orders = order_book.get_orders_by_user(user)
        orders = {order.id: order.__json__() for order in orders}
        self.write(orders)

    msg_type_handlers = {b"H": order_stats, b"V": market_data, b"AF": user_data}

    def get(self):
        message = parse_message(self.request)

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (f"/{config['TRADING_SESSION']}", TradeHandler),
        (f"/{config['QUOTE_SESSION']}", QuoteHandler)
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(config["PORT"], address=config["HOST"].replace("http://", ""))
    print(f"Server started on {config['HOST']}:{config['PORT']}")
    tornado.ioloop.IOLoop.current().start()
