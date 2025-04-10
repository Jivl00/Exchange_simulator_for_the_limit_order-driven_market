from src.client.algorithmic_trader import AlgorithmicTrader
import json


class RangeTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, support_level=99, resistance_level=101):
        """
        Initializes the RangeTrader.
        :param name: Name of the agent
        :param server: Server name
        :param config: Configuration dictionary
        :param support_level: Price threshold for buying
        :param resistance_level: Price threshold for selling
        """
        super().__init__(name, server, config)
        self.support_level = support_level
        self.resistance_level = resistance_level
        self.prices = {}

    def handle_market_data(self, message):
        """
        Handles incoming market data - storing bid and ask prices for the product.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]
        if product not in self.prices:
            self.prices[product] = {"bid": 0, "ask": 0}
        if mid_price := self.mid_price():
            self.prices[product]["bid"] = message["order_book"]["Bids"][0]["Price"]
            self.prices[product]["ask"] = message["order_book"]["Asks"][0]["Price"]
            self.delete_dispensable_orders(product, mid_price, 1, 60)

    def trade(self, message):
        """
        Executes the trading strategy based on the market data and support/resistance levels.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]
        bid_price, ask_price = self.prices[product]["bid"], self.prices[product]["ask"]

        # Make trading decisions based on support and resistance levels
        if bid_price < self.support_level: # Buy
            quantity = self.compute_quantity(product, "buy", bid_price)
            if quantity > 0:
                self.put_order({"side": "buy", "quantity": quantity, "price": bid_price}, product)
        elif ask_price >= self.resistance_level: # Sell
            quantity = self.compute_quantity(product, "sell", ask_price)
            if quantity > 0:
                self.put_order({"side": "sell", "quantity": quantity, "price": ask_price}, product)

config = json.load(open("../config/server_config.json"))
swing_trader = RangeTrader("range_trader", "server", config)
swing_trader.register(1000)
swing_trader.start_subscribe()

