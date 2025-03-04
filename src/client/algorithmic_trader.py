from abc import abstractmethod
from src.client.client import Trader

class AlgorithmicTrader (Trader):
    """
    Interface for algorithmic trading agents.
    Must implement:
    - handle_market_data
    - trade
    """
    def __init__(self, name, server, config):
        """
        :param name:  Name of the agent
        :param server:  Server name
        :param config:  Configuration dictionary
        """
        super().__init__(name, server, config)
        self.current_mid_prices = {}

    def receive_market_data(self, message):
        """
        Receives market data and updates stored market information.
        :param message:  Market data message
        """
        bids = message["order_book"]["Bids"]
        asks = message["order_book"]["Asks"]
        print(f"Received order book: {message}")
        product = message["product"]
        if bids and asks:
            self.current_mid_prices[product] = (bids[0]["price"] + asks[0]["price"]) / 2
        else:
            self.current_mid_prices[product] = None
        self.handle_market_data(message)
        self.trade()

    # @abstractmethod
    def handle_market_data(self, message):
        """
        Handles incoming market data.
        :param message:  Market data message - dictionary with keys "product", "order_book"
        """
        pass

    # @abstractmethod
    def trade(self):
        """
        Executes trading strategy.
        """
        pass