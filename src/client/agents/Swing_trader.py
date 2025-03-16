from src.client.algorithmic_trader import AlgorithmicTrader
import json


class SwingTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, support_level=100, resistance_level=200):
        super().__init__(name, server, config)
        self.support_level = support_level
        self.resistance_level = resistance_level
        self.products = set()

    def handle_market_data(self, message):
        product = message["product"]
        self.products.add(product)

    def trade(self):
        pass
        for product in self.products:
            if product not in self.current_mid_price:
                continue
            if self.current_mid_price[product] and self.current_mid_price[product] < self.support_level: # Buy
                self.put_order({"side": "buy", "quantity": 100, "price": self.current_mid_price[product]}, product)
            elif self.current_mid_price[product] and self.current_mid_price[product] >= self.resistance_level: # Sell
                self.put_order({"side": "sell", "quantity": 100, "price": self.current_mid_price[product]}, product)

config = json.load(open("config/server_config.json"))
momentum_trader = SwingTrader("swing_trader", "server", config)
momentum_trader.start_subscribe()

