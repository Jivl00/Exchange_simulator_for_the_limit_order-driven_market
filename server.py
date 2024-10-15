import tornado.ioloop
import tornado.web
import tornado.websocket
import json
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize an empty order book and matching engine
order_book = OrderBook()
fifo_matching_engine = FIFOMatchingEngine(order_book)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Welcome to the trading server!")

class AddOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        order = Order(data['id'], data['timestamp'], data['side'], data['quantity'], data['price'])
        order_book.add_order(order)
        self.write({"message": "Order added successfully"})

class ModifyOrderQtyHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        order_book.modify_order_qty(data['order_id'], new_quantity=data['new_quantity'])
        self.write({"message": "Order quantity modified successfully"})

class MatchOrderHandler(tornado.web.RequestHandler):
    def post(self):
        data = json.loads(self.request.body)
        order = Order(data['id'], data['timestamp'], data['side'], data['quantity'], data['price'])
        fifo_matching_engine.match_order(order)
        self.write({"message": "Order matched successfully"})

class DisplayOrderBookHandler(tornado.web.RequestHandler):
    def get(self):
        order_book_data = order_book.jsonify_order_book()  # Assuming this method returns the order book data as a dictionary
        self.write(order_book_data)

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/add_order", AddOrderHandler),
        (r"/modify_order_qty", ModifyOrderQtyHandler),
        (r"/match_order", MatchOrderHandler),
        (r"/display_order_book", DisplayOrderBookHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()