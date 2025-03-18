from src.client.algorithmic_trader import AlgorithmicTrader
import json


class SwingTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, support_level=99, resistance_level=101):
        super().__init__(name, server, config)
        self.support_level = support_level
        self.resistance_level = resistance_level
        self.products = set()

    def handle_market_data(self, message):
        product = message["product"]
        self.products.add(product)
        print(self.user_balance(product)["current_balance"])

    def trade(self):
        # pass
        for product in self.products:
            if product not in self.current_mid_price:
                continue
            if self.current_mid_price[product] and self.current_mid_price[product] < self.support_level: # Buy
                quantity = self.compute_quantity(product, "buy", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": self.current_mid_price[product]}, product)
            elif self.current_mid_price[product] and self.current_mid_price[product] >= self.resistance_level: # Sell
                quantity = self.compute_quantity(product, "sell", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": self.current_mid_price[product]}, product)

config = json.load(open("config/server_config.json"))
swing_trader = SwingTrader("swing_trader", "server", config)
swing_trader.register(1000)
swing_trader.start_subscribe()

