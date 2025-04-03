import json
import numpy as np
import time
from src.client.algorithmic_trader import AlgorithmicTrader


class ScalpingTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, spread_factor=0.0002, trade_interval=0.5, volatility_lookback=20):
        """
        Initializes the ScalpingTrader.
        :param name: Name of the agent
        :param server: Server name
        :param config: Configuration dictionary
        :param spread_factor: Percentage of the spread to use for placing orders in relation to the mid price
        :param trade_interval: Minimum time interval between trades in seconds
        :param volatility_lookback: Number of historical prices to consider for volatility calculation
        """
        super().__init__(name, server, config)
        self.spread_factor = spread_factor
        self.trade_interval = trade_interval
        self.volatility_lookback = volatility_lookback
        self.last_trade_time = {}
        self.price_history = {}

    def handle_market_data(self, message):
        """
        Handles incoming market data.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]

        if product not in self.price_history:
            self.price_history[product] = []
        if mid_price := self.mid_price():
            self.price_history[product].append(mid_price)

            # Trim the price history to the lookback period
            self.price_history[product] = self.price_history[product][-self.volatility_lookback:]

            self.delete_dispensable_orders(product, mid_price, 1, 10)

    def trade(self, message):
        """
        Executes the trading strategy based on market data.
        :param message:
        :return:
        """

        product = message["product"]
        if (product in self.last_trade_time and
            time.time() - self.last_trade_time[product] < self.trade_interval):
            return

        if not self.mid_price():
            return

        volatility = np.std(self.price_history[product][-self.volatility_lookback:])
        adaptive_spread = self.spread_factor * (1 + volatility)

        mid_price = self.mid_price()
        buy_price = mid_price * (1 - adaptive_spread)
        sell_price = mid_price * (1 + adaptive_spread)

        quantity = self.compute_quantity(product, "buy", buy_price)
        if quantity > 0:
            self.put_order({"type": "limit", "side": "buy", "quantity": quantity, "price": buy_price}, product)

        quantity = self.compute_quantity(product, "sell", sell_price)
        if quantity > 0:
            self.put_order({"type": "limit", "side": "sell", "quantity": quantity, "price": sell_price}, product)

        self.last_trade_time[product] = time.time()


config = json.load(open("../config/server_config.json"))
scalping_trader = ScalpingTrader("scalping_trader", "server", config)
scalping_trader.register(1000)
scalping_trader.start_subscribe()
