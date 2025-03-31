import numpy as np
import json
from src.client.algorithmic_trader import AlgorithmicTrader

class RSITRader(AlgorithmicTrader):
    def __init__(self, name, server, config, period=14, overbought=70, oversold=30):
        super().__init__(name, server, config)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.prices = {}

    def handle_market_data(self, message):
        product = message["product"]
        if product not in self.prices:
            self.prices[product] = []
        if self.current_mid_price[product]:
            self.prices[product].append(self.current_mid_price[product])
        if len(self.prices[product]) > self.period:
            self.prices[product] = self.prices[product][1:]

    def calculate_rsi(self, prices):
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)

        avg_gain = np.mean(gain[-self.period:])
        avg_loss = np.mean(loss[-self.period:])
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def trade(self):
        for product in self.prices:
            if len(self.prices[product]) < self.period:
                continue
            if self.current_mid_price[product] is None:
                continue
            rsi = self.calculate_rsi(self.prices[product])
            if rsi < self.oversold:  # Buy
                quantity = self.compute_quantity(product, "buy", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": self.current_mid_price[product]}, product)
            elif rsi > self.overbought:  # Sell
                quantity = self.compute_quantity(product, "sell", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": self.current_mid_price[product]}, product)

config = json.load(open("../config/server_config.json"))
RSI_trader = RSITRader("RSI_trader", "server", config)
RSI_trader.register(1000)
RSI_trader.start_subscribe()