import numpy as np

from src.client.algorithmic_trader import AlgorithmicTrader
import json


class EMATrader(AlgorithmicTrader):
    def __init__(self, name, server, config, short_window=5, long_window=20):
        super().__init__(name, server, config)
        self.short_window = short_window
        self.long_window = long_window
        self.prices = {}

    def handle_market_data(self, message):
        product = message["product"]
        if product not in self.prices:
            self.prices[product] = []
        if self.current_mid_price[product]:
            self.prices[product].append(self.current_mid_price[product])
        if len(self.prices[product]) > self.long_window:
            self.prices[product] = self.prices[product][1:]
        print(self.user_balance(product, verbose=False)["current_balance"])
        self.delete_dispensable_orders(product, self.current_mid_price[product], 1, 60)

    def trade(self):
        for product in self.prices:
            if len(self.prices[product]) < self.long_window:
                continue
            if self.current_mid_price[product] is None:
                continue
            short_ema = self.calculate_ema(self.prices[product], self.short_window)
            long_ema = self.calculate_ema(self.prices[product], self.long_window)
            if short_ema > long_ema: # Buy
                quantity = self.compute_quantity(product, "buy", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": self.current_mid_price[product]}, product)
            elif short_ema < long_ema: # Sell
                quantity = self.compute_quantity(product, "sell", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": self.current_mid_price[product]}, product)

    def calculate_ema(self, prices, window):
        weights = np.exp(np.linspace(-1., 0., window))
        weights /= weights.sum()
        ema = np.convolve(prices, weights, mode='valid')
        return ema[-1]

config = json.load(open("config/server_config.json"))
EMA_trader = EMATrader("EMA_trader", "server", config)
EMA_trader.register(1000)
EMA_trader.start_subscribe()

