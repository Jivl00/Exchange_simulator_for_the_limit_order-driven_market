import numpy as np
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
        self.trade(message)

    def put_order(self, order, product):
        """
        Places an order.
        :param order:  Order dictionary
        :param product:  Product name
        """
        print(f"Placing order: {order} for product: {product}")
        return super().put_order(order, product)

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

    def imbalance_index(self, asks, bids, alpha=0.5, level=3):
        """
        Calculate imbalance index for a given orderbook.
        :param asks: list of ask sizes (quantities)
        :param bids: list of bid sizes (quantities)
        :param alpha: parameter for imbalance index
        :param level: number of levels to consider
        :return: imbalance index
        """
        bids = bids[:level]
        asks = asks[:level]
        exp_factors = np.exp(-alpha * np.arange(level))

        # Calculate imbalance index
        V_bt = sum(bids * exp_factors[:len(bids)])
        V_at = sum(asks * exp_factors[:len(asks)])
        return (V_bt - V_at) / (V_bt + V_at)


    def bid_ask_trade(self, current_prices, predicted_prices, price_threshold, product):
        """
        Executes trading strategy based on bid-ask prices.
        :param current_prices:  Tuple of current bid and ask prices
        :param predicted_prices:  Tuple of predicted bid and ask prices
        :param price_threshold:  Price threshold for trading
        :param product:  Product name
        """
        predicted_bid, predicted_ask = predicted_prices
        current_bid, current_ask = current_prices

        # Sell when predicted bid > current bid
        if predicted_bid > current_bid + price_threshold:
            quantity = self.compute_quantity(product, "sell", predicted_bid)
            if quantity > 0:
                self.put_order({"side": "sell", "quantity": quantity, "price": predicted_bid}, product)

        # Buy when predicted ask < current ask
        if predicted_ask < current_ask - price_threshold:
            quantity = self.compute_quantity(product, "buy", predicted_ask)
            if quantity > 0:
                self.put_order({"side": "buy", "quantity": quantity, "price": predicted_ask}, product)

    # @abstractmethod
    def handle_market_data(self, message):
        """
        Handles incoming market data.
        :param message:  Market data message - dictionary with keys "product", "order_book"
        """
        pass

    # @abstractmethod
    def trade(self, message):
        """
        Executes trading strategy.
        """
        pass