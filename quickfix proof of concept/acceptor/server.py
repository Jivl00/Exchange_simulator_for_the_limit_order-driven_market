"""Client FIX"""
import sys
import quickfix
from application import Application
import tornado.ioloop
import tornado.web
import tornado.websocket
from web_server import make_app, OrderBookWebSocketHandler

def main():
    """Main"""
    config_file = "server.cfg"
    try:
        settings = quickfix.SessionSettings(config_file)
        application = Application()
        storefactory = quickfix.FileStoreFactory(settings)
        logfactory = quickfix.FileLogFactory(settings)
        acceptor = quickfix.SocketAcceptor(application, storefactory, settings, logfactory)

        acceptor.start()

        # Start Tornado application
        app = make_app()
        app.listen(8888)
        print("Tornado server is running on http://localhost:8888")
        ioloop = tornado.ioloop.IOLoop.current()
        OrderBookWebSocketHandler.ioloop = ioloop
        ioloop.start()


        application.run()
        acceptor.stop()


    except (quickfix.ConfigError, quickfix.RuntimeError) as e:
        print(e)
        acceptor.stop()
        sys.exit()


if __name__ == '__main__':
    main()