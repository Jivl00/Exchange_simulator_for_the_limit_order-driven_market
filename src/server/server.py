import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import logging
import time
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
from src.protocols.fix import FIXProtocol

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# TODO log outcoming messages as debug

config = json.load(open("config/server_config.json"))
BEGIN_STRING = "8=FIX.4.4"
MSG_SEQ_NUM = 0
ID = 0

order_book = OrderBook()
fifo_matching_engine = FIFOMatchingEngine(order_book)
protocol = FIXProtocol("server")


class MainHandler(tornado.web.RequestHandler):
    """
    Main handler for the web server.
    """
    def get(self):
        self.write("This is the trading server")


class TradingHandler(tornado.web.RequestHandler):

    def match_order(self, message):
        global ID
        message = protocol.decode(message)
        order = Order(
            str(ID),
            time.time_ns(),
            message["order"]["user"],
            message["order"]["side"],
            message["order"]["quantity"],
            message["order"]["price"]
        )
        ID += 1
        status = fifo_matching_engine.match_order(order)
        protocol.set_target(message["order"]["user"])
        return protocol.encode({"order_id": order.id, "status": status, "msg_type": "ExecutionReport"})

    def delete_order(self, message):
        message = protocol.decode(message)
        order_id = message["order_id"]
        order = order_book.get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportCancel"})
        order_book.delete_order(order_id)
        protocol.set_target(order.user)
        return protocol.encode({"order_id": order_id, "status": True, "msg_type": "ExecutionReportCancel"})


    def modify_order_qty(self, message):
        message = protocol.decode(message)
        order_id = message["order_id"]
        quantity = message["quantity"]
        order = order_book.get_order_by_id(order_id)
        if order is None:
            return protocol.encode({"order_id": order_id, "status": False, "msg_type": "ExecutionReportModify"})
        ret = order_book.modify_order_qty(order_id, quantity)
        protocol.set_target(order.user)
        return protocol.encode({"order_id": order_id, "status": True, "msg_type": "ExecutionReportModify"})


    msg_type_handlers = {
        "NewOrderSingle": match_order,
        "OrderCancelRequest": delete_order,
        "OrderModifyRequestQty": modify_order_qty,
    }
    def post(self):
        message = json.loads(self.request.body)
        logging.info(f"R> {message['message']}")
        msg_type = message["msg_type"]
        message = self.msg_type_handlers[msg_type](self, message)
        logging.debug(f"S> {message}")
        self.write({"message": message.decode()})


class QuoteHandler(tornado.web.RequestHandler):

    def order_stats(self, message):
        message = protocol.decode(message)
        order_id = message["id"]
        order = order_book.get_order_by_id(order_id)
        protocol.set_target(message["sender"])
        return protocol.encode({"order": order, "msg_type": "OrderStatus"})

    def order_book_request(self, message):
        order_book_data = order_book.jsonify_order_book()
        return protocol.encode({"order_book": order_book_data, "msg_type": "MarketDataSnapshot"})

    def user_data(self, message):
        message = protocol.decode(message)
        user_orders = order_book.get_orders_by_user(message["user"])
        user_orders = {order.id: order.__json__() for order in user_orders}
        protocol.set_target(message["user"])
        return protocol.encode({"user_orders": user_orders, "msg_type": "UserOrderStatus"})

    msg_type_handlers = {
        "OrderStatusRequest": order_stats,
        "MarketDataRequest": order_book_request,
        "UserOrderStatusRequest": user_data
    }
    def get(self):
        message = json.loads(self.request.body)
        logging.info(f"R> {message['message']}")
        msg_type = message["msg_type"]
        message = self.msg_type_handlers[msg_type](self,message)
        logging.debug(f"S> {message}")
        self.write({"message": message.decode()})


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