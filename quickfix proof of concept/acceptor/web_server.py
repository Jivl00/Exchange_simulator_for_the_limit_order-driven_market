# acceptor/web_server.py
import json

import tornado.web
import tornado.websocket


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")
class OrderBookWebSocketHandler(tornado.websocket.WebSocketHandler):
    clients = set()
    ioloop = None

    def open(self):
        OrderBookWebSocketHandler.clients.add(self)
        print("WebSocket opened, total clients: %d" % len(OrderBookWebSocketHandler.clients))

    def on_close(self):
        OrderBookWebSocketHandler.clients.remove(self)
        print("WebSocket closed, total clients: %d" % len(OrderBookWebSocketHandler.clients))

    @classmethod
    def send_updates(cls, message):
        print("Sending message to %d clients" % len(cls.clients))
        for client in cls.clients:
            if client.ws_connection:
                formatted_message = json.dumps({"message": message})
                print("Sending message to client: %s" % formatted_message)
                cls.ioloop.add_callback(client.write_message, formatted_message)
            else:
                print("Client connection is not active")


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/order_book_ws", OrderBookWebSocketHandler),
    ], template_path="templates")