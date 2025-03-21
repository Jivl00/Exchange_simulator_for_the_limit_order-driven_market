import json
import unittest
import subprocess
import time
from src.client.algorithmic_trader import AlgorithmicTrader
from src.client.client import AdminTrader

# TODO test put order status
"""

Scenario 2: User Order Book and Balance Evaluation

    Objective: Test order book retrieval, order placing, and balance evaluation.

    Register a new user with a budget of 1000.
    Check the order book for a specific product to see the available prices and quantities.
    Based on the order book, compute the quantity to buy using the user's balance.
    Place a buy order using the computed quantity.
    Retrieve the user’s balance after placing the order.
    Check the order status of the newly placed order.

Scenario 3: Historical Order Books and Cleanup

    Objective: Retrieve historical order books, identify dispensable orders, and delete them.

    Register a new user with a budget of 500.
    Place multiple buy orders at various prices for a product.
    Retrieve the historical order books for a product (with a lookback of 60 entries).
    Identify orders that are dispensable based on a price threshold of 5 units.
    Delete the dispensable orders and print the list of deleted orders.
    Verify the user’s balance after the cleanup.

Scenario 4: Full Order Lifecycle with Multiple Modifications

    Objective: Test multiple order modifications in a single session.

    Register a new user with a budget of 2000.
    Place a buy order for a product at a price of 100 and quantity of 10.
    Modify the order’s price to 105.
    Further modify the order’s quantity to 15.
    Retrieve the order’s status after each modification.
    Delete the order.
    Check the user’s balance after the order is deleted.

Scenario 5: Bulk Order Management

    Objective: Test placing, modifying, and deleting multiple orders for a product.

    Register a new user with a budget of 3000.
    Place 5 buy orders with varying quantities and prices for a product.
    Retrieve the status of all 5 orders.
    Modify 2 of the orders: change the price and quantity.
    Delete one of the orders after modification.
    Check the user’s balance after some orders are deleted.

Scenario 6: Dynamic Order Calculation with Price Thresholds

    Objective: Simulate dynamic trading where the quantity to be traded is based on available balance and order book data.

    Register a new user with a budget of 1000.
    Retrieve the order book for a product.
    Based on the order book and user balance, compute the quantity of product the user can afford.
    Place a buy order for the computed quantity.
    After the order is placed, check the status and balance.
    If the current market price is above the user's budget, delete the order.

Scenario 7: Order Book Modification and Disposal

    Objective: Test placing orders, modifying them, and removing dispensable orders based on current price and age.

    Register a new user with a budget of 1500.
    Place an initial buy order for a product at a price of 100.
    Modify the price of the order based on market conditions.
    After a certain period, check if any orders are dispensable (either due to price or age).
    Delete the dispensable orders.
    Check the user’s balance after deleting dispensable orders.

Scenario 8: Advanced Order Handling with Order Book Analysis

    Objective: Test a more advanced scenario that combines order book analysis with order placement and modification.

    Register a new user with a budget of 2000.
    Retrieve the current order book for a product and analyze the top 3 levels for the best prices.
    Calculate the quantity that can be bought based on available budget and top 3 order book prices.
    Place a buy order based on the computed quantity.
    After some time, modify the order to adjust the price based on the new order book data.
    Delete the order after modifications if the price no longer aligns with the best available price.

Scenario 9: Trade Completion and Clean-Up

    Objective: Test the end-to-end process from placing an order to completing a trade (deleting dispensable orders).

    Register a new user with a budget of 5000.
    Place a buy order for a product at the market price.
    Retrieve the order status to check if the order is partially or fully filled.
    If the order is fully filled, delete it from the order book.
    Retrieve and display the user’s balance after the trade is complete.

Scenario 10: Rebalancing Portfolio

    Objective: Simulate the process of rebalancing a portfolio by modifying orders and checking balance.

    Register a new user with a budget of 10000.
    Place multiple orders for various products (buy and sell orders).
    Modify orders to ensure they align with portfolio goals.
    Delete orders that are no longer needed (either because they are unfilled or unnecessary).
    Check the balance after rebalancing and ensure the portfolio is as desired.
"""
class TestAdminTrader(AdminTrader):
    def receive_market_data(self, data):
        # Implement the abstract method
        pass

class TestAlgorithmicTraderIntegration(unittest.TestCase):
    server_process = None
    @classmethod
    def setUpClass(cls):
        # Start the server using subprocess
        print("Starting the server...")
        # TODO: Change the path to python.exe based on your environment
        cls.server_process = subprocess.Popen(["C:\\Users\\vladka\\PycharmProjects\\pythonProject\\venv\\Scripts"
                                               "\\python.exe", "..\src\server\server.py"])
        # cls.server_process = subprocess.Popen(["python.exe", "..\src\server\server.py"])
        time.sleep(5)  # Allow server time to start

        config = json.load(open("../config/server_config.json"))
        cls.trader = AlgorithmicTrader("TestTrader", "Server1", config)
        cls.tester = TestAdminTrader("liquidity_generator", "Server1", config)
        cls.tester.initialize_liquidity_engine(10000, 10000)
        print("Initialized AlgorithmicTrader for Integration Tests")

    @classmethod
    def tearDownClass(cls):
        """Terminate the server after tests are complete"""
        print("Shutting down the server...")
        cls.server_process.terminate()
        cls.server_process.wait()

    def test_scenario_1(self):
        """
        Scenario 1: New User Trading Cycle

        Objective: Test the process of registering a user, placing an order,
                   modifying the order, checking order status, and then deleting it.

        Register a new user with a budget of 1000.
        Place a buy order for a product at a price of 100 and quantity of 5.
        Check the status of the order.
        Modify the order to change the price to 110.
        Delete the modified order.
        Check the user balance after the order is deleted.
        """
        # 1. Register a new user with a budget of 1000
        user_id = self.trader.register(1000)
        self.assertIsNotNone(user_id)
        print(f"User registered with ID: {user_id}")

        # 2. Place a buy order for a product at a price of 100 and quantity of 5
        order_details = {
            "price": 100,
            "quantity": 5,
            "side": "buy"
        }
        order_id, status = self.trader.put_order(order_details, "product1")
        if status:
            print(f"Order placed with ID: {order_id}")

        # 3. Check the status of the order
        order_status = self.trader.order_stats(order_id, "product1")
        self.assertIsNotNone(order_status)
        self.assertEqual(order_status["price"], 100)
        self.assertEqual(order_status["quantity"], 5)
        self.assertEqual(order_status["side"], "buy")
        print(f"Order status: {order_status}")

        # 4. Modify the order to change the price to 110 and check the status
        new_order_id, status = self.trader.modify_order(order_id, "product1", new_price=110)
        self.assertIsNotNone(new_order_id)
        print(f"Order modified. New Order ID: {new_order_id}")
        order_status = self.trader.order_stats(new_order_id, "product1")
        self.assertEqual(order_status["price"], 110)

        # 5. Delete the modified order
        result = self.trader.delete_order(new_order_id, "product1")
        self.assertTrue(result)
        print(f"Order {new_order_id} deleted successfully")

        # 6. Check the user balance after the order is deleted (should be 1000 - fees)
        balance = self.trader.user_balance("product1")
        self.assertIsNotNone(balance)
        print(f"User balance: {balance}")
        post_buy_budget = balance["post_buy_budget"]
        self.assertGreaterEqual(post_buy_budget, 999)

    def test_scenario_2(self):
        """
        Scenario 2: User Order Book and Balance Evaluation

        Objective: Test order book retrieval, order placing, and balance evaluation.

        Register a new user with a budget of 1000.
        Check the order book for a specific product to see the available prices and quantities.
        Based on the order book, compute the quantity to buy using the user's balance.
        Place a buy order using the computed quantity.
        Retrieve the user’s balance after placing the order.
        """
        # 1. Register a new user with a budget of 1000
        user_id = self.trader.register(1000)
        self.assertIsNotNone(user_id)
        print(f"User registered with ID: {user_id}")

        # Artificially fill the order book with some data
        self.tester.put_order({"price": 100, "quantity": 10, "side": "sell"}, "product1")
        self.tester.put_order({"price": 98, "quantity": 5, "side": "buy"}, "product1")

        # 2. Check the order book for a specific product
        order_book = self.trader.order_book_request("product1")
        self.assertIsNotNone(order_book)
        print(f"Order book: {order_book}")

        # 3. Compute the quantity to buy using the user's balance
        quantity = self.trader.compute_quantity("product1", "buy", 100, ratio=0.5)
        self.assertEqual(quantity, 5) # 50% of the budget or max quantity in the order book which is 10
        print(f"Computed quantity: {quantity}")

        # 4. Place a buy order using the computed quantity
        order_details = {
            "price": 100,
            "quantity": quantity,
            "side": "buy"
        }
        order_id, status = self.trader.put_order(order_details, "product1")
        self.assertIsNotNone(order_id)
        print(f"Order placed with ID: {order_id}")

        # 5. Retrieve the user’s balance after placing the order
        balance = self.trader.user_balance("product1")["current_balance"]["balance"]
        self.assertEqual(balance, -500) # 5*100 = 500 spent
        print(f"User balance: {balance}")


if __name__ == '__main__':
    unittest.main()
