from sklearn.linear_model import LinearRegression, Ridge, Lasso, BayesianRidge
from sklearn.ensemble import RandomForestRegressor
import numpy as np
import json
from src.client.algorithmic_trader import AlgorithmicTrader


class RegressionTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, base_window_size=10, model_type="linear", price_threshold=0.01):
        """
        Initializes the RegressionTrader.
        :param name:  Name of the agent
        :param server:  Server name
        :param config:  Configuration dictionary
        :param base_window_size:  Initial window size
        :param model_type:  Type of regression model to use: "linear", "ridge", "lasso", "bayesian", "random_forest"
        :param price_threshold:  Price threshold for trading
        """
        super().__init__(name, server, config)
        self.base_window_size = base_window_size
        self.window_size = base_window_size
        self.price_threshold = price_threshold
        self.prices = {}
        self.volumes = {}

        # Select the regression model dynamically
        self.model = self.select_model(model_type)

    def select_model(self, model_type):
        """
        Initialize the selected regression model.
        :param model_type:  Type of regression model to use (linear, ridge, lasso, bayesian, random_forest)
        """
        models = {
            "linear": LinearRegression(),
            "ridge": Ridge(alpha=1.0),
            "lasso": Lasso(alpha=0.1),
            "bayesian": BayesianRidge(),
            "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
        }
        return models.get(model_type, LinearRegression())  # Default to Linear Regression

    def handle_market_data(self, message):
        """
        Handles incoming market data.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]
        order_book = message["order_book"]
        if product not in self.prices:
            self.prices[product] = {"mid": [], "bid": [], "ask": []}
            self.volumes[product] = {"bid": [], "ask": []}

        if not order_book["Bids"] or not order_book["Asks"]:
            return
        bid_price = order_book["Bids"][0]["Price"]
        ask_price = order_book["Asks"][0]["Price"]
        bid_volume = order_book["Bids"][0]["Quantity"]
        ask_volume = order_book["Asks"][0]["Quantity"]

        if mid_price := self.mid_price():
            self.prices[product]["mid"].append(mid_price)
            self.prices[product]["bid"].append(bid_price)
            self.prices[product]["ask"].append(ask_price)
            self.volumes[product]["bid"].append(bid_volume)
            self.volumes[product]["ask"].append(ask_volume)

            # Delete dispensable orders
            self.delete_dispensable_orders(product, mid_price, 1, 60)

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
        """
        Predicts the next price based on the given prices and volumes.
        :param prices: List of prices
        :param volumes: List of volumes
        :return: Predicted price
        """
        x = np.array(range(len(prices))).reshape(-1, 1)  # Time steps
        y = np.array(prices).reshape(-1, 1)
        weights = np.array(volumes).reshape(-1, 1)  # Volume-weighted regression

        model = LinearRegression()
        model.fit(x, y, sample_weight=weights.flatten())

        return model.predict(np.array([[len(prices)]]))[0][0]

    def trade(self, message):
        """
        Executes trading strategy - sell when predicted bid > current bid, buy when predicted ask < current ask.
        """
        product = message["product"]
        if len(self.prices[product]["mid"]) < self.window_size:
            return # Not enough data for prediction

        predicted_bid = self.predict_price(self.prices[product]["bid"], self.volumes[product]["bid"])
        predicted_ask = self.predict_price(self.prices[product]["ask"], self.volumes[product]["ask"])
        current_bid = self.prices[product]["bid"][-1]
        current_ask = self.prices[product]["ask"][-1]

        self.bid_ask_trade((current_bid, current_ask), (predicted_bid, predicted_ask), self.price_threshold, product)

# Setup and run the RegressionTrader
config = json.load(open("../config/server_config.json"))
r_trader = RegressionTrader("lr_trader", "server", config, model_type="random_forest")
r_trader.register(10000)
r_trader.start_subscribe()
