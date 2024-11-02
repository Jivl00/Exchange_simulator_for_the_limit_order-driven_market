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

# Initialize an empty order book and matching engine
order_book = OrderBook()
fifo_matching_engine = FIFOMatchingEngine(order_book)
ID = 0

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class KeepAliveHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.write_message("Connection established")

    def on_message(self, message):
        self.write_message("Message received")

    def on_close(self):
        self.write_message("Connection closed")

class ModifyOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        timestamp = time.time_ns() # nanoseconds since epoch
        order_book.modify_order(data['order_id'], timestamp, new_price=data['new_price'], new_quantity=data['new_quantity'])
        self.write({"message": "Order modified successfully"})

class ListUserOrdersHandler(tornado.web.RequestHandler):
    def get(self):
        user = self.get_argument('user')
        orders = order_book.get_order_by_user(user)
        orders = {order.id: order.__str__() for order in orders}
        self.write(orders)


class DisplayOrderBookHandler(tornado.web.RequestHandler):
    def get(self):
        order_book_data = order_book.jsonify_order_book()  # Assuming this method returns the order book data as a dictionary
        self.write(order_book_data)


def make_order(data):
    """
    Create an order object from the FIX message
    :param data: FIX message data
    :return: Order object
    """
    global ID
    timestamp = time.time_ns()
    side = data.get(54) # 54 = Side
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


class FixHandler(tornado.web.RequestHandler):
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
        fifo_matching_engine.match_order(order)
        # TODO print execution of the order, return ID of the order
        self.write({"message": "Order added successfully"})

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
            # new_price = data.get(44)
            # new_quantity = data.get(38)
            # print(new_price, new_quantity)
            # if new_price is not None:
            #     new_price = float(new_price.decode())
            # if new_quantity is not None:
            #     new_quantity = int(new_quantity.decode())
            # print(new_price, new_quantity)
            # timestamp = time.time_ns()
            # ret = order_book.modify_order(order_id, timestamp, new_price=new_price, new_quantity=new_quantity)
            # if ret:
            #     self.write({"message": "Order modified successfully"})
            # else:
            #     self.write({"message": "Order modification failed, order not found"})

    msg_type_handlers = {b"D": match_order, b"F": delete_order, b"G": modify_order_qty, b"H": order_stats}
    def post(self):
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
        (r"/keep_alive", KeepAliveHandler),
        (r"/modify_order", ModifyOrderHandler),
        (r"/list_user_orders", ListUserOrdersHandler),
        (r"/display_order_book", DisplayOrderBookHandler),
        (r"/fix", FixHandler)
    ], template_path="templates")

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()