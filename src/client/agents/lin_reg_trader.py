from sklearn.linear_model import LinearRegression
import numpy as np
import json
from src.client.algorithmic_trader import AlgorithmicTrader


class LinearRegressionTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, base_window_size=10):
        super().__init__(name, server, config)
        self.base_window_size = base_window_size  # Base window size
        self.window_size = base_window_size  # Will be dynamically adjusted
        self.prices = {}  # Stores price history
        self.volumes = {}  # Stores volume history

    def handle_market_data(self, message):
        product = message["product"]
        bid_price = message["order_book"]["Bids"][0]["Price"]
        ask_price = message["order_book"]["Asks"][0]["Price"]
        bid_volume = message["order_book"]["Bids"][0]["Quantity"]
        ask_volume = message["order_book"]["Asks"][0]["Quantity"]

        if product not in self.prices:
            self.prices[product] = {"mid": [], "bid": [], "ask": []}
            self.volumes[product] = {"bid": [], "ask": []}
        if mid_price := self.mid_price():
            self.prices[product]["mid"].append(mid_price)
            self.prices[product]["bid"].append(bid_price)
            self.prices[product]["ask"].append(ask_price)
            self.volumes[product]["bid"].append(bid_volume)
            self.volumes[product]["ask"].append(ask_volume)

            # Adjust window size dynamically based on volatility (rolling standard deviation)
            if len(self.prices[product]["mid"]) > 2:
                vol = np.std(self.prices[product]["mid"][-self.window_size:])
                self.window_size = max(5, min(50, int(self.base_window_size + 100 * vol)))

            # Trim history to maintain the adjusted window size
            for key in ["mid", "bid", "ask"]:
                self.prices[product][key] = self.prices[product][key][-self.window_size:]
            for key in ["bid", "ask"]:
                self.volumes[product][key] = self.volumes[product][key][-self.window_size:]

    def predict_price(self, prices, volumes):
        x = np.array(range(len(prices))).reshape(-1, 1)  # Time steps
        y = np.array(prices).reshape(-1, 1)
        weights = np.array(volumes).reshape(-1, 1)  # Volume-weighted regression

        model = LinearRegression()
        model.fit(x, y, sample_weight=weights.flatten())

        return model.predict(np.array([[len(prices)]]))[0][0]

    def trade(self):
        for product in self.prices:
            if len(self.prices[product]["mid"]) < self.window_size:
                continue

            predicted_bid = self.predict_price(self.prices[product]["bid"], self.volumes[product]["bid"])
            predicted_ask = self.predict_price(self.prices[product]["ask"], self.volumes[product]["ask"])
            current_bid = self.prices[product]["bid"][-1]
            current_ask = self.prices[product]["ask"][-1]

            # Buy when predicted bid > current bid
            if predicted_bid > current_bid:
                quantity = self.compute_quantity(product, "sell", predicted_bid)
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": predicted_bid}, product)

            # Sell when predicted ask < current ask
            if predicted_ask < current_ask:
                quantity = self.compute_quantity(product, "buy", predicted_ask)
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": predicted_ask}, product)


# Setup and run the Linear Regression Trader
config = json.load(open("../config/server_config.json"))
lr_trader = LinearRegressionTrader("lr_trader", "server", config)
lr_trader.register(10000)
lr_trader.start_subscribe()
