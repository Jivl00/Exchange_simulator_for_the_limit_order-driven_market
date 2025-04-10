import json
from src.client.algorithmic_trader import AlgorithmicTrader

class Printer(AlgorithmicTrader):
    def __init__(self, name, server, config):
        """
        Initializes the Printer agent.
        :param name: Name of the agent
        :param server: Server name
        :param config: Configuration dictionary
        """
        super().__init__(name, server, config)

    def handle_market_data(self, message):
        """
        Handles incoming market data and prints it to the console.
        :param message: Market data message - dictionary with keys "product", "order_book"
        """
        product = message["product"]
        order_book = message["order_book"]

        # Print the market data
        print(f"Market Data for {product}:")
        self.display_order_book(order_book, product=product, aggregated=False)

    def trade(self, message):
        pass


# Initialize the Printer agent
config = json.load(open("../config/server_config.json"))
printer_agent = Printer("test_trader", "server", config)
printer_agent.register()
printer_agent.start_subscribe()