import json
import random
import time

from src.client.algorithmic_trader import AlgorithmicTrader

class SpoofingTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, spoof_size=50, real_size=5, spoof_distance=0.02, order_frequency=5, max_orders=5):
        """
        Initializes the SpoofingTrader.
        :param name: Name of the agent
        :param server: Server name
        :param config: Configuration dictionary
        :param spoof_size: Size of the spoof order
        :param real_size: Size of the real order
        :param spoof_distance: Distance from mid-price to place spoof orders
        :param order_frequency: Frequency of placing orders in seconds
        :param max_orders: Maximum number of spoof orders to place
        """
        super().__init__(name, server, config)
        self.spoof_size = spoof_size
        self.real_size = real_size
        self.spoof_distance = spoof_distance
        self.order_frequency = order_frequency
        self.max_orders = max_orders

        self.spoof_orders = {}
        self.last_order_time = time.time()

    def handle_market_data(self, message):
        """
        Handle incoming market data.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]
        if mid_price := self.mid_price():
            self.delete_dispensable_orders(product, mid_price, 0.01, 30)
    def trade(self, message):
        """
        Execute the spoofing strategy:
        - Place spoof orders (large, away from market)
        - Place real orders (small, marketable)
        - Cancel spoof orders
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]

        current_time = time.time()
        if current_time - self.last_order_time < self.order_frequency: # Avoid placing orders too frequently
            return

        if (mid_price := self.mid_price()) is None:
            return

        self.last_order_time = current_time

        # Decide spoof and real sides
        spoof_side = "sell"
        owned_volume = self.user_balance(product, False)["current_balance"]["post_sell_volume"]
        if owned_volume > self.real_size:
            spoof_side = "buy"
        real_side = "sell" if spoof_side == "buy" else "buy"
        direction = -1 if spoof_side == "buy" else 1

        for _ in range(random.randint(1, self.max_orders)):
            spoof_price = round(mid_price * (1 + direction * self.spoof_distance), 2)

            # Place spoof order (large, away from market)
            spoof_order = {
                "side": spoof_side,
                "quantity": random.randint(self.spoof_size // 2, self.spoof_size),
                "price": spoof_price
            }
            spoof_order_id, status = self.put_order(spoof_order, product)
            if status is True:
                self.spoof_orders[product] = [spoof_order_id]

        # Place real order (small, marketable)
        direction = -1 * direction
        real_price = round(mid_price * (1 + direction * self.spoof_distance), 2)
        real_order = {
            "side": real_side,
            "quantity": random.randint(self.real_size // 2, self.real_size),
            "price": real_price
        }
        self.put_order(real_order, product)

        # Cancel spoof orders
        if product in self.spoof_orders:
            for order_id in self.spoof_orders[product]:
                self.delete_order(order_id, product)
            self.spoof_orders[product] = []

if __name__ == "__main__":
    config = json.load(open("../config/server_config.json"))
    spoofing_trader = SpoofingTrader("spoofing_trader", "server", config, spoof_distance=0.015)
    spoofing_trader.register(100000)
    spoofing_trader.start_subscribe()
