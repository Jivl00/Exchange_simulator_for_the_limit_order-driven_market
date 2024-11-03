import tornado.ioloop
import tornado.web
import tornado.websocket
import json
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
import logging
import time
import simplefix

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# TODO log outcoming messages as debug

# Initialize an empty order book and matching engine
order_book = OrderBook()
fifo_matching_engine = FIFOMatchingEngine(order_book)
ID = 0


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


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


class TradeHandler(tornado.web.RequestHandler):
    # TODO fix message response to client
    parser = simplefix.FixParser()

    def order_stats(self, data):
        order_id = data.get(41).decode()
        order = order_book.get_order_by_id(order_id)
        if order:
            self.write({"order": order.__json__()})
        else:
            self.write({"message": "Order not found"})

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
        data = json.loads(self.request.body)
        message = data['message']
        self.parser.append_buffer(message)
        message = self.parser.get_message()
        logging.info(f"Received message: {message}")

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)

    def get(self):
        data = json.loads(self.request.body)
        message = data['message']
        self.parser.append_buffer(message)
        message = self.parser.get_message()
        logging.info(f"Received message: {message}")

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)


class QuoteHandler(tornado.web.RequestHandler):
    parser = simplefix.FixParser()

    def order_stats(self, data):
        order_id = data.get(41).decode()
        order = order_book.get_order_by_id(order_id)
        if order:
            self.write({"order": order.__json__()})
        else:
            self.write({"message": "Order not found"})

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
        data = json.loads(self.request.body)
        message = data['message']
        self.parser.append_buffer(message)
        message = self.parser.get_message()
        logging.info(f"Received message: {message}")

        msg_type_handler = self.msg_type_handlers[message.get(35)]
        msg_type_handler(self, message)


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/trade", TradeHandler),
        (r"/quote", QuoteHandler),
    ], template_path="templates")


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
