import pandas as pd

from src.client.algorithmic_trader import AlgorithmicTrader
import json
import numpy as np
class SwingTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, lookback=20, bollinger_std=2, confirm_ticks=3):
        """
        Initializes the SwingTrader with additional indicators.
        :param name: Name of the agent
        :param server: Server name
        :param config: Configuration dictionary
        :param lookback: Number of historical prices to consider
        :param bollinger_std: Standard deviation multiplier for Bollinger Bands
        :param confirm_ticks: Number of ticks to confirm breakout
        """
        super().__init__(name, server, config)
        self.lookback = lookback
        self.bollinger_std = bollinger_std
        self.confirm_ticks = confirm_ticks
        self.mid_prices = {}

    def handle_market_data(self, message):
        """
        Handles incoming market data - storing mid prices for the product.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]

        # Initialize data structures for the product if not already
        if product not in self.mid_prices:
            self.mid_prices[product] = []

        if mid_price := self.mid_price():
            self.mid_prices[product].append(mid_price)
            self.mid_prices[product] = self.mid_prices[product][-self.lookback:]
            self.delete_dispensable_orders(product, mid_price, 1, 60)

    def compute_bollinger_bands(self, prices):
        """
        Compute the Bollinger Bands (upper, middle, lower) for the given prices.
        :param prices: List of historical prices
        :return: Upper band, middle band, lower band
        """
        rolling_mean = np.mean(prices)
        rolling_std = np.std(prices)
        upper_band = rolling_mean + self.bollinger_std * rolling_std
        lower_band = rolling_mean - self.bollinger_std * rolling_std
        return upper_band, rolling_mean, lower_band

    def compute_fibonacci_levels(self, high, low):
        """
        Compute Fibonacci retracement levels based on high and low.
        :param high: The recent high price
        :param low: The recent low price
        :return: A dictionary of Fibonacci retracement levels
        """
        diff = high - low
        fib_levels = {
            "23.6%": high - 0.236 * diff,
            "38.2%": high - 0.382 * diff,
            "50%": high - 0.5 * diff,
            "61.8%": high - 0.618 * diff
        }
        return fib_levels

    def trade(self, message):
        """
        Executes the trading strategy based on Bollinger Bands, Fibonacci, and Imbalance Index.
        """
        product = message["product"]
        prices = self.mid_prices[product]

        if len(prices) < self.lookback:
            return  # Not enough data to make a trade

        # Compute Bollinger Bands, Fibonacci Levels, and Imbalance Index
        upper_band, middle_band, lower_band = self.compute_bollinger_bands(prices)
        high = max(prices[-self.lookback:])
        low = min(prices[-self.lookback:])
        fib_levels = self.compute_fibonacci_levels(high, low)

        bids = message["order_book"]["Bids"]
        asks = message["order_book"]["Asks"]
        if not bids or 'Quantity' not in bids[0] or not asks or 'Quantity' not in asks[0]:
            return

        bids_df = pd.DataFrame(bids)
        asks_df = pd.DataFrame(asks)
        imbalance_index = self.imbalance_index(asks_df['Quantity'].values, bids_df['Quantity'].values)

        # Trade logic
        mid_price = prices[-1]
        if mid_price < lower_band and imbalance_index < -0.2 and mid_price < fib_levels["38.2%"]:
            quantity = self.compute_quantity(product, "buy", mid_price)
            if quantity > 0:
                self.put_order({"type": "limit", "side": "buy", "quantity": quantity, "price": mid_price}, product)
        elif mid_price > upper_band and imbalance_index > 0.2 and mid_price > fib_levels["61.8%"]:
            quantity = self.compute_quantity(product, "sell", mid_price)
            if quantity > 0:
                self.put_order({"type": "limit", "side": "sell", "quantity": quantity, "price": mid_price}, product)




# Initialize and run the SwingTrader
config = json.load(open("../config/server_config.json"))
swing_trader = SwingTrader("swing_trader", "server", config)
swing_trader.register(1000)
swing_trader.start_subscribe()
