import numpy as np
import json
from src.client.algorithmic_trader import AlgorithmicTrader
class BollingerBandsTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, window=20, num_std_dev=2):
        super().__init__(name, server, config)
        self.window = window
        self.num_std_dev = num_std_dev
        self.prices = {}

    def handle_market_data(self, message):
        product = message["product"]
        if product not in self.prices:
            self.prices[product] = []
        if self.current_mid_price[product]:
            self.prices[product].append(self.current_mid_price[product])
        if len(self.prices[product]) > self.window:
            self.prices[product] = self.prices[product][1:]

    def calculate_bollinger_bands(self, prices):
        rolling_mean = np.mean(prices[-self.window:])
        rolling_std = np.std(prices[-self.window:])
        upper_band = rolling_mean + (self.num_std_dev * rolling_std)
        lower_band = rolling_mean - (self.num_std_dev * rolling_std)
        return upper_band, lower_band

    def trade(self):
        for product in self.prices:
            if len(self.prices[product]) < self.window:
                continue
            if self.current_mid_price[product] is None:
                continue
            upper_band, lower_band = self.calculate_bollinger_bands(self.prices[product])
            if self.current_mid_price[product] < lower_band:  # Buy
                quantity = self.compute_quantity(product, "buy", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": self.current_mid_price[product]}, product)
            elif self.current_mid_price[product] > upper_band:  # Sell
                quantity = self.compute_quantity(product, "sell", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": self.current_mid_price[product]}, product)

config = json.load(open("../config/server_config.json"))
BollingerBands_trader = BollingerBandsTrader("BollingerBands_trader", "server", config)
BollingerBands_trader.register(1000)
BollingerBands_trader.start_subscribe()