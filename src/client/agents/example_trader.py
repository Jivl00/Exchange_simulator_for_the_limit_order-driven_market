import json

from src.client.algorithmic_trader import AlgorithmicTrader


class YourTraderName(AlgorithmicTrader):
    def __init__(self, name, server, config):  # Feel free to add any parameters you need
        super().__init__(name, server, config)

    def handle_market_data(self, message):
        """
        Called automatically whenever new market data arrives.

        :param message: A dictionary containing market info, with keys:
                        - "product": Name of the traded asset
                        - "order_book": The current order book (bids/asks)

        This method is useful for:
        - Analyzing live market conditions
        - Tracking price trends
        - Updating internal strategy state

        You *must* implement this method.
        """
        # You can ignore the product since we are only trading on one product
        product = message["product"]
        order_book = message["order_book"]

        # Display raw order book data in the terminal for debugging/monitoring
        print(f"Market Data for {product}:")
        self.display_order_book(order_book, product=product, aggregated=False)

        # Feel free to store/compute any data you need for your strategy
        # Some indicators are already available in the AlgorithmicTrader class for example mid_price

        # You can also use the following method to delete orders that are no longer relevant
        # self.delete_dispensable_orders() # Read method description in Trader class for more details

    def trade(self, message):
        """
        Called periodically to make trading decisions.

        :param message: A dictionary containing market info, with keys:
                        - "product": Name of the traded asset
                        - "order_book": The current order book (bids/asks)

        Your trading logic goes here — you can:
        - Analyze market state
        - Use indicators or signals
        - Place, modify, or cancel orders

        Useful built-in methods:
        - self.compute_quantity(): Helps determine safe trade sizes
        - self.put_order(): Places a new limit order (buy/sell)
        - self.delete_order(): Cancels an existing order
        - self.modify_order(): Changes an existing order
        - you can find more in the Trader class (src/client/client.py)
        """
        pass


# Load trading configuration
# Make sure you run this file from the project root (src/) so the path works correctly
config = json.load(open("../config/server_config.json"))

# Instantiate your trading bot
your_trader = YourTraderName("trader", "server", config)

# Authenticate using your UUID — make sure to replace this with your actual ID
your_trader.login_via_UUID("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

# DON'T USE THE REGISTER METHOD IT'S ONLY FOR MY PREMADE TRADERS

# Start receiving market data and begin trading
your_trader.start_subscribe()
