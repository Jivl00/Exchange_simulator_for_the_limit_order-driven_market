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
        self.current_order_book = {}

    def receive_market_data(self, message):
        """
        Receives market data and updates stored market information.
        :param message:  Market data message
        """
        self.current_order_book = message["order_book"]
        self.handle_market_data(message)
        self.trade()

    def put_order(self, order, product):
        """
        Places an order.
        :param order:  Order dictionary
        :param product:  Product name
        """
        super().put_order(order, product)
        print(f"Placing order: {order} for product: {product}")

    def mid_price(self):
        """
        Returns the mid-price of the current order book.
        :return:  Mid-price or None if not available
        """
        bids = self.current_order_book["Bids"]
        asks = self.current_order_book["Asks"]
        if bids and asks:
            return (bids[0]["Price"] + asks[0]["Price"]) / 2
        else:
            return None


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