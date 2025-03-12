import logging
import random
import time
from abc import ABC
import json

from src.client.client import Trader
from src.server.server import products

logging.getLogger("urllib3").setLevel(logging.WARNING) # suppress logging


class SyntheticLiquidityProvider(Trader, ABC):
    def __init__(self, target, config):
        super().__init__("liquidity_generator", target, config)

    def get_top_of_the_book(self, product):
        return self.order_book_request(product, depth=10) # get top of the order book

    def receive_market_data(self, data):
        pass

    def generate_liquidity(self):
        while True:
            time.sleep(random.randint(1, 5)) # sleep for 1-5 seconds
            product = random.choice(products) # randomly select a product to trade
            product = "product1" # TODO: Remove this line
            order_book = self.get_top_of_the_book(product) # get top of the order book
            print(order_book)
            side = random.choice(["buy", "sell"]) # randomly select a side
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

            price = price + random.uniform(-0.1, 0.1) # add some noise to the price
            # randomly select a quantity
            quantity = random.randint(1, 100)
            # place order
            self.put_order({"side": side, "quantity": quantity, "price": price}, product)
            logging.info(f"Synthetic liquidity added: {side} order at {price} for {quantity} {product}")

config = json.load(open("config/server_config.json"))
liquidity_generator = SyntheticLiquidityProvider("server", config)
liquidity_generator.generate_liquidity()
