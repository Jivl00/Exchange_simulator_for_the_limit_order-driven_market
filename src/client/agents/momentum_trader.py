from src.client.algorithmic_trader import AlgorithmicTrader
import json


class MomentumTrader(AlgorithmicTrader):
    def __init__(self, name, server, config, lookback=5):
        super().__init__(name, server, config)
        self.lookback = lookback
        self.momentum = {}

    def handle_market_data(self, message):
        product = message["product"]
        if product not in self.momentum:
            self.momentum[product] = []
        if self.current_mid_price[product]:
            self.momentum[product].append(self.current_mid_price[product])
        if len(self.momentum[product]) > self.lookback:
            self.momentum[product] = self.momentum[product][1:]
        print(self.user_balance(product, verbose=False)["current_balance"])
        self.delete_dispensable_orders(product, self.current_mid_price[product], 1, 60)

    def trade(self):
        for product in self.momentum:
            if len(self.momentum[product]) < self.lookback:
                continue
            if self.current_mid_price[product] is None:
                continue
            price_change = self.momentum[product][-1] - self.momentum[product][0]
            if price_change > 0: # Buy
                quantity = self.compute_quantity(product, "buy", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "buy", "quantity": quantity, "price": self.current_mid_price[product]}, product)
            elif price_change < 0: # Sell
                quantity = self.compute_quantity(product, "sell", self.current_mid_price[product])
                if quantity > 0:
                    self.put_order({"side": "sell", "quantity": quantity, "price": self.current_mid_price[product]}, product)

config = json.load(open("config/server_config.json"))
momentum_trader = MomentumTrader("momentum_trader", "server", config)
momentum_trader.register(1000)
momentum_trader.start_subscribe()

