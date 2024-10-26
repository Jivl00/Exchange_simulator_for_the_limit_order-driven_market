"""FIX Application"""
import quickfix as fix
import time

import tornado

from web_server import OrderBookWebSocketHandler
from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order

import logging

def setup_logger(logger_name, log_file, level=logging.DEBUG):
    lz = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    lz.setLevel(level)
    lz.addHandler(fileHandler)
    lz.addHandler(streamHandler)

# Start of Header
__SOH__ = chr(1)

setup_logger('logfix', 'logs/message.log')
logfix = logging.getLogger('logfix')


class Application(fix.Application):
    """FIX Application"""
    sessionID = None
    orderID = 0
    order_book = OrderBook()
    fifo_matching_engine = FIFOMatchingEngine(order_book)

    def onCreate(self, sessionID):
        """onCreate"""
        print("onCreate : Session (%s)" % sessionID.toString())
        return

    def onLogon(self, sessionID):
        self.sessionID = sessionID
        print("Successful Logon to session '%s'." % sessionID.toString())
        """onLogon"""
        return

    def onLogout(self, sessionID):
        """onLogout"""
        print("Logout from session '%s'." % sessionID.toString())
        return

    def toAdmin(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.debug("(Admin) S >> %s" % msg)
        return

    def fromAdmin(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.debug("(Admin) R << %s" % msg)
        return

    def toApp(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.debug("(App) S >> %s" % msg)
        return

    def fromApp(self, message, sessionID):
        msg = message.toString().replace(__SOH__, "|")
        logfix.debug("(App) R << %s" % msg)
        self.onMessage(message, sessionID)
        return

    def onMessage(self, message, sessionID):
        '''Processing application message'''
        if message.getHeader().getField(35) == 'D':  # Assuming 'D' is the message type for AddOrder
            OrderBookWebSocketHandler.send_updates(message.toString())
        pass

    def run(self):
        """Run"""
        import threading
        web_server_thread = threading.Thread(target=tornado.ioloop.IOLoop.current().start)
        web_server_thread.start()

        while True:
            time.sleep(1)