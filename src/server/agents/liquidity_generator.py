import logging
import random
import time
from abc import ABC
import json
import os
import sys

import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.client.client import AdminTrader
from src.server.server import products

logging.getLogger("urllib3").setLevel(logging.WARNING) # suppress logging


class SyntheticLiquidityProvider(AdminTrader, ABC):
    def __init__(self, target, config):
        super().__init__("liquidity_generator", target, config)
        self.initialize_liquidity_engine(10000, 10000) # initialize liquidity engine

    def get_top_of_the_book(self, product):
        return self.order_book_request(product, depth=10)

    def receive_market_data(self, data):
        pass

    def generate_liquidity(self):
        while True:
            time.sleep(random.randint(1, 5)) # sleep for 1-5 seconds
            product = random.choice(products) # randomly select a product to trade
            product = "product1" # TODO: Remove this line
            order_book = self.get_top_of_the_book(product) # get top of the order book
            bid_volume = sum([order["Quantity"] for order in order_book["Bids"]])
            ask_volume = sum([order["Quantity"] for order in order_book["Asks"]])
            side = np.random.choice(["sell", "buy"], p=[bid_volume / (bid_volume + ask_volume), ask_volume / (bid_volume + ask_volume)])
            # randomly select a price
            if side == "buy":
                if order_book["Bids"]:
                    price = order_book["Bids"][0]["Price"]
                elif order_book["Asks"]:
                    price = order_book["Asks"][0]["Price"]
                else:
                    continue  # Skip this iteration if both Bids and Asks are empty
            else:
                if order_book["Asks"]:
                    price = order_book["Asks"][0]["Price"]
                elif order_book["Bids"]:
                    price = order_book["Bids"][0]["Price"]
                else:
                    continue  # Skip this iteration if both Bids and Asks are empty
            self.delete_dispensable_orders(product, price, 1, 30)
            price = price + random.uniform(-0.1, 0.1) # add some noise to the price
            quantity = self.compute_quantity(product, side, price)
            if quantity > 0:
                self.put_order({"side": side, "quantity": quantity, "price": price}, product)
                logging.info(f"Synthetic liquidity added: {side} order at {price} for {quantity} {product}")
                # print(self.user_balance(product)["current_balance"])

if __name__ == "__main__":
    config = json.load(open("../config/server_config.json"))
    liquidity_generator = SyntheticLiquidityProvider("server", config)
    liquidity_generator.generate_liquidity()
