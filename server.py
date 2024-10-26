import tornado.ioloop
import tornado.web
import tornado.websocket
import json
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
import logging
import time

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

class AddOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        global ID
        timestamp = time.time_ns() # nanoseconds since epoch
        order = Order(ID, timestamp, data['user'], data['side'], data['quantity'], data['price'])
        ID += 1
        fifo_matching_engine.match_order(order)
        # TODO print execution of the order
        self.write({"message": "Order added successfully"})

class ModifyOrderQtyHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        order_book.modify_order_qty(data['order_id'], new_quantity=data['new_quantity'])
        self.write({"message": "Order quantity modified successfully"})

class ModifyOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        timestamp = time.time_ns() # nanoseconds since epoch
        order_book.modify_order(data['order_id'], timestamp, new_price=data['new_price'], new_quantity=data['new_quantity'])
        self.write({"message": "Order modified successfully"})

class DeleteOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        order_book.delete_order(data['order_id'])
        self.write({"message": "Order deleted successfully"})

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

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/keep_alive", KeepAliveHandler),
        (r"/add_order", AddOrderHandler),
        (r"/modify_order_qty", ModifyOrderQtyHandler),
        (r"/modify_order", ModifyOrderHandler),
        (r"/delete_order", DeleteOrderHandler),
        (r"/list_user_orders", ListUserOrdersHandler),
        (r"/display_order_book", DisplayOrderBookHandler),
    ], template_path="templates")

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()