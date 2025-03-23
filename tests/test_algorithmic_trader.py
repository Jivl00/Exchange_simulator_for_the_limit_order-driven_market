import json
import unittest
import subprocess
import time
import logging
from src.client.algorithmic_trader import AlgorithmicTrader
from src.client.client import AdminTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#TODO: better assert messages + more tests
class TestAdminTrader(AdminTrader):
    def receive_market_data(self, data):
        # Implement the abstract method
        pass


class TestAlgorithmicTraderIntegration(unittest.TestCase):
    server_process = None

    @classmethod
    def setUpClass(cls):
        # Start the server using subprocess
        logger.info("Starting the server...")
        # TODO: Change the path to python.exe based on your environment
        cls.server_process = subprocess.Popen(
            ["C:\\Users\\vladka\\PycharmProjects\\pythonProject\\venv\\Scripts\\python.exe", "..\src\server\server.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # cls.server_process = subprocess.Popen(["python.exe", "..\src\server\server.py"])
        time.sleep(5)  # Allow server time to start

        config = json.load(open("../config/server_config.json"))
        cls.trader = AlgorithmicTrader("TestTrader", "Server1", config)
        cls.tester = TestAdminTrader("liquidity_generator", "Server1", config)
        cls.tester.initialize_liquidity_engine(10000, 10000)
        logger.info("Initialized AlgorithmicTrader for Integration Tests")

    @classmethod
    def tearDownClass(cls):
        """
        Terminate the server after tests are complete
        """
        logger.info("Shutting down the server...")
        cls.server_process.terminate()
        cls.server_process.wait()

    def setUp(self):
        """
        Ensure a clean test state before each test.
        """
        self.addCleanup(self.clean_up)

    def register_user(self, budget):
        """
        Registers a new user and returns the user ID.
        """
        user_id = self.trader.register(budget)
        self.assertIsNotNone(user_id, "User registration failed.")
        logger.info(f"User registered with ID: {user_id}")
        return user_id

    def clean_up(self):
        """
        Clean up by removing all orders after each test.
        """
        logger.info("Cleaning up after the test...")
        for trader in [self.trader, self.tester]:
            all_orders = trader.list_user_orders("product1")
            for order_id in all_orders:
                trader.delete_order(order_id, "product1")

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
        self.register_user(1000)

        # 2. Place a buy order for a product at a price of 100 and quantity of 5
        order_details = {
            "price": 100,
            "quantity": 5,
            "side": "buy"
        }
        order_id, status = self.trader.put_order(order_details, "product1")
        if status:
            logger.info(f"Order placed with ID: {order_id}")

        # 3. Check the status of the order
        order_status = self.trader.order_stats(order_id, "product1")
        self.assertIsNotNone(order_status)
        self.assertEqual(order_status["price"], 100)
        self.assertEqual(order_status["quantity"], 5)
        self.assertEqual(order_status["side"], "buy")
        logger.info(f"Order status: {order_status}")

        # 4. Modify the order to change the price to 110 and check the status
        new_order_id, status = self.trader.modify_order(order_id, "product1", new_price=110)
        self.assertIsNotNone(new_order_id)
        logger.info(f"Order modified. New Order ID: {new_order_id}")
        order_status = self.trader.order_stats(new_order_id, "product1")
        self.assertEqual(order_status["price"], 110)

        # 5. Delete the modified order
        result = self.trader.delete_order(new_order_id, "product1")
        self.assertTrue(result)
        logger.info(f"Order {new_order_id} deleted successfully")

        # 6. Check the user balance after the order is deleted (should be 1000 - fees)
        balance = self.trader.user_balance("product1", verbose=False)
        self.assertIsNotNone(balance)
        logger.info(f"User balance: {balance}")
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
        self.register_user(1000)

        # Artificially fill the order book with some data
        self.tester.put_order({"price": 100, "quantity": 10, "side": "sell"}, "product1")
        self.tester.put_order({"price": 98, "quantity": 5, "side": "buy"}, "product1")

        # 2. Check the order book for a specific product
        order_book = self.trader.order_book_request("product1")
        self.assertIsNotNone(order_book)
        logger.info(f"Order book: {order_book}")

        # 3. Compute the quantity to buy using the user's balance
        quantity = self.trader.compute_quantity("product1", "buy", 100, ratio=0.5)
        self.assertEqual(quantity, 5)  # 50% of the budget or max quantity in the order book which is 10
        logger.info(f"Computed quantity: {quantity}")

        # 4. Place a buy order using the computed quantity
        order_details = {
            "price": 100,
            "quantity": quantity,
            "side": "buy"
        }
        order_id, status = self.trader.put_order(order_details, "product1")
        self.assertIsNotNone(order_id)
        logger.info(f"Order placed with ID: {order_id}")

        # 5. Retrieve the user’s balance after placing the order
        balance = self.trader.user_balance("product1", verbose=False)["current_balance"]["balance"]
        self.assertEqual(balance, -500)  # 5*100 = 500 spent
        logger.info(f"User balance: {balance}")


    def test_scenario_3(self):
        """
        Scenario 3: Bulk Order Management

        Objective: Test placing and retrieving multiple orders for a product.

        Register a new user with a budget of 3000.
        Place 5 buy orders with varying quantities and prices for a product.
        Retrieve the status of all 5 orders.
        """
        # 1. Register a new user with a budget of 3000
        self.register_user(3000)

        # Artificially fill the order book with some data
        self.tester.put_order({"price": 101, "quantity": 10, "side": "sell"}, "product1")
        self.tester.put_order({"price": 100, "quantity": 5, "side": "sell"}, "product1")
        self.tester.put_order({"price": 98, "quantity": 10, "side": "buy"}, "product1")
        self.tester.put_order({"price": 99, "quantity": 5, "side": "buy"}, "product1")

        # 2. Place 5 buy orders with varying quantities and prices for a product
        orders = [
            {"price": 102, "quantity": 14, "side": "buy"},  # Fully filled
            {"price": 101, "quantity": 5, "side": "buy"},  # Partially filled
            {"price": 98, "quantity": 15, "side": "sell"},  # Fully filled
            {"price": 103, "quantity": 20, "side": "sell"},  # Failed - insufficient volume
            {"price": -10, "quantity": -25, "side": "side"}  # Invalid order
        ]

        # 3. Retrieve the status of all 5 orders
        expected_statuses = [None, True, None, False, False]
        order_ids = []
        for i, order in enumerate(orders):
            order_id, status = self.trader.put_order(order, "product1")
            # self.trader.display_order_book(self.trader.order_book_request("product1"))
            active_orders = self.trader.list_user_orders("product1")
            if i != 1:
                self.assertEqual(active_orders, {}, "Expected no active orders")
            else:
                self.assertEqual(len(active_orders), 1)
                self.assertEqual(list(active_orders.keys())[0], order_id)
            self.assertEqual(status, expected_statuses[i])
            order_ids.append(order_id)
            logger.info(f"Order {i + 1} placed with ID: {order_id}")


    def test_scenario_4(self):
        """
        Scenario 4: Historical Order Books and Cleanup

        Objective: Retrieve historical order books

        Register a new user with a budget of 500.
        Place multiple buy orders at various prices for a product.
        Retrieve the historical order books for a product (with a lookback of 60 entries).
        """
        # 1. Register a new user with a budget of 500
        self.register_user(500)

        # 2. Place multiple buy orders at various prices for a product
        orders = [
            {"price": 10, "quantity": 5, "side": "buy"},
            {"price": 11, "quantity": 1, "side": "buy"},
            {"price": 12, "quantity": 5, "side": "buy"},
            {"price": 13, "quantity": 2, "side": "buy"},
            {"price": 14, "quantity": 5, "side": "buy"},
            {"price": 15, "quantity": 3, "side": "buy"},
            {"price": 16, "quantity": 5, "side": "buy"},
            {"price": 17, "quantity": 4, "side": "buy"},
            {"price": 18, "quantity": 5, "side": "buy"},
            {"price": 19, "quantity": 5, "side": "buy"},
            {"price": 10, "quantity": 5, "side": "buy"},
            {"price": 11, "quantity": 6, "side": "buy"},
            {"price": 12, "quantity": 6, "side": "buy"},
            {"price": 13, "quantity": 7, "side": "buy"},
            {"price": 14, "quantity": 7, "side": "buy"},
            {"price": 15, "quantity": 8, "side": "buy"},
            {"price": 16, "quantity": 5, "side": "buy"},
            {"price": 17, "quantity": 9, "side": "buy"},
            {"price": 18, "quantity": 9, "side": "buy"},
            {"price": 19, "quantity": 1, "side": "buy"},
            {"price": 20, "quantity": 5, "side": "buy"},
            {"price": 21, "quantity": 1, "side": "buy"},
            {"price": 22, "quantity": 1, "side": "buy"}]

        for i, order in enumerate(orders):
            self.tester.put_order(order, "product1")

        historical_order_books = self.trader.historical_order_books("product1", 20, verbose=False)
        self.assertEqual(len(historical_order_books), 21)  # 20 + 1 current order book
        logger.info(f"Retrieved {len(historical_order_books)} historical order books")

        # Verify the order books
        for i, order_book in enumerate(historical_order_books):
            self.assertTrue(order_book)


if __name__ == '__main__':
    unittest.main()
