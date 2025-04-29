from src.client.client import Trader


class WebTrader(Trader):
    """
    WebTrader is a subclass of Trader that implements the web client for trading.
    """
    def __init__(self, name, mode, config):
        super().__init__(name, mode, config)

    def receive_market_data(self, data):
        pass # Not needed for web client