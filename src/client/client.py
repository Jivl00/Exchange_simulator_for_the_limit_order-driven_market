import json
import asyncio
import inspect
import requests
import pandas as pd
from abc import ABC, abstractmethod
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.websocket import websocket_connect
from src.protocols.FIXProtocol import FIXProtocol


class Subscriber(ABC):
    """
    Subscriber class for subscribing to the trading server for updates on orders and trades.
    """
    def __init__(self, url, protocol, timeout=1):
        """
        Initialize the subscriber.
        :param url: URL to connect to
        :param protocol: Protocol object for encoding and decoding messages
        :param timeout: Timeout in seconds for maintaining the connection (heartbeats)
        """
        self.url = url
        self.protocol = protocol
        self.loop = IOLoop.instance()
        self.ws = None
        asyncio.ensure_future(self.connect())
        timeout = timeout * 1000  # to seconds
        PeriodicCallback(self.maintain_connection, timeout).start()

    def start_subscribe(self):
        """
        Start the subscription loop.
        """
        self.loop.start()

    async def connect(self):
        """
        Connect to the server via WebSocket.
        """
        try:
            self.ws = await websocket_connect(self.url)
        except Exception as e:
            print(f"Connection error: {e}")
        else:
            print("Subscription successful")
            await self.subscribe()

    async def maintain_connection(self):
        """
        Send a heartbeat message to the server to maintain the connection.
        """
        if self.ws is None:
            await self.connect()
        else:
            await self.ws.write_message("Heartbeat")

    async def subscribe(self):
        """
        Subscribe to the server for updates.
        """
        while True: # Keep the connection open
            msg = await self.ws.read_message()
            if msg is None:
                print("Connection closed")
                self.ws = None
                break
            if msg == ">Heartbeat":
                continue
            data = json.loads(msg)
            data["msg_type"] = "MarketDataSnapshot"
            data = self.protocol.decode(data)
            product = data["product"]
            order_book_data = data["order_book"]
            Trader.display_order_book(order_book_data, product=product)
            self.receive_market_data(data)

    @abstractmethod
    def receive_market_data(self, data):
        """
        Handle market data received from the server.
        :param data: JSON with market data
        """
        pass

    def __del__(self):
        """
        Destructor - close the WebSocket connection.
        """
        if self.ws is not None:
            self.ws.close()



class Trader (Subscriber, ABC):
    """
    Client class for communicating with the trading server.
    """

    def __init__(self, sender, target, config):
        """
        Initialize the client.
        :param sender: Sender ID (Client ID)
        :param target: Target ID (Server ID)
        :param config: Configuration dictionary with server details, e.g. HOST, PORT, TRADING_SESSION, QUOTE_SESSION
        """
        self.PROTOCOL = FIXProtocol(sender, target)
        super().__init__(f"ws://{config['HOST'].replace('http://', '')}:{config['PORT']}/websocket", self.PROTOCOL)
        self.BASE_URL = f"{config['HOST']}:{config['PORT']}"
        self.TRADING_SESSION = config["TRADING_SESSION"]
        self.QUOTE_SESSION = config["QUOTE_SESSION"]

    @staticmethod
    def parse_response(response):
        """
        Parse the response from the server.
        :param response: Response from the server
        :return: JSON with response data if successful, None otherwise
        """
        caller = inspect.stack()[1].function
        response = response.json()
        if "error" in response:
            print(f"\033[91mError in {caller}: {response['error']}\033[0m")  # Print in red
            return None
        return response

    def register(self, budget):
        """
        Register a new user with the server.
        :param budget: Initial budget
        :return: Unique user ID if successful, None otherwise
        """
        data = {"budget": budget, "msg_type": "RegisterRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}",
                                 json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "RegisterResponse"
        response_data = self.PROTOCOL.decode(response)
        print(f"User registered with ID: {response_data['user']}")
        # Change the user ID to the unique user ID returned by the server
        self.PROTOCOL.set_sender(response_data["user"])
        return response_data["user"]

    def order_stats(self, ID, product):
        """
        Request order status from the server.
        :param ID: Order ID
        :param product: Product name
        :return: JSON with order details (id, timestamp, user, side, quantity, price) if found, None otherwise
        """
        data = {"ID": ID, "product": product, "msg_type": "OrderStatusRequest"}
        message = self.PROTOCOL.encode(data)

        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}",
                                json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "OrderStatus"
        order = self.PROTOCOL.decode(response)
        return order

    def put_order(self, order, product):
        """
        Send a new order request to the server.
        :param order: Dictionary containing order details
        :param product: Product name
        :return: Order ID if not fully filled, None otherwise
        """
        # Check if the user has enough volume to place the order
        if order["side"] == "sell":
            user_balance = self.user_balance(product, verbose=False)["history_balance"][-1]["volume"]
            if order["quantity"] > user_balance:
                print("\033[91mError: Insufficient order volume.\033[0m")  # Print in red
                # return None

        data = {"order": order, "product": product, "msg_type": "NewOrderSingle"}
        message = self.PROTOCOL.encode(data)

        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}",
                                 json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "ExecutionReport"
        response_data = self.PROTOCOL.decode(response)
        if response_data is None or response_data.get("status") is False:
            print("\033[91mError: Order put failed. Please check the order details and remaining balance.\033[0m")
            return None

        return response_data["order_id"] if response_data["status"] else None

    def delete_order(self, ID, product):
        """
        Send an order cancel request to the server.
        :param ID: Order ID
        :param product: Product name
        :return: True if successful, False otherwise
        """
        data = {"ID": ID, "product": product, "msg_type": "OrderCancelRequest"}
        message = self.PROTOCOL.encode(data)

        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}",
                                 json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "ExecutionReportCancel"
        response_data = self.PROTOCOL.decode(response)
        return response_data["status"]

    def modify_order_qty(self, ID, quantity, product):
        """
        Modify order quantity - only decrease is allowed.
        :param ID: Order ID
        :param quantity: New quantity
        :param product: Product name
        :return: True if successful, False otherwise
        """
        data = {"ID": ID, "quantity": quantity, "product": product, "msg_type": "OrderModifyRequestQty"}
        message = self.PROTOCOL.encode(data)
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}",
                                 json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "ExecutionReportModify"
        response_data = self.PROTOCOL.decode(response)
        return response_data["status"]

    def modify_order(self, ID, product, new_price=None, new_quantity=None):
        """
        Modify an existing order - price and/or quantity.
        :param ID: Order ID
        :param product: Product name
        :param new_price: New price (or None)
        :param new_quantity: New quantity (or None)
        :return: Order ID if not fully filled, None otherwise
        """
        order = self.order_stats(ID, product)
        if order is None:
            print(f"\033[91mError: Order {ID} not found.\033[0m")
            return None
        self.delete_order(ID, product)
        if new_price is not None:
            order['price'] = new_price
        if new_quantity is not None:
            order['quantity'] = new_quantity
        return self.put_order(order, product)

    def order_book_request(self, product, depth=0):
        """
        Returns the order book for a specific product from the server.
        :param product: Product name
        :param depth: Market depth (0 = full book)
        :return: JSON with order book data
        """
        data = {"depth": depth, "product": product, "msg_type": "MarketDataRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}",
                                json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        order_book_data = response
        order_book_data["msg_type"] = "MarketDataSnapshot"
        order_book_data = self.PROTOCOL.decode(order_book_data)["order_book"]

        return order_book_data

    def list_user_orders(self, product):
        """
        Returns a list of orders for a specific user.
        :param product: Product name
        :return: JSON with order data
        """
        data = {"product": product, "msg_type": "UserOrderStatusRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}",
                                json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        print("response", response)
        response["msg_type"] = "UserOrderStatus"
        data = self.PROTOCOL.decode(response)
        data = data["user_orders"]
        print(pd.DataFrame(data).T)
        return data

    def user_balance(self, product, verbose=True):
        """
        Returns the user's balance for a specific product.
        Last element in the list is current balance and volume - therefore no timestamp is needed.
        :param product: Product name
        :param verbose: If True, print the user's balance
        :return: array with user's balance if successful, None otherwise
        """
        data = {"product": product, "msg_type": "UserBalanceRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}",
                                json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "UserBalance"
        data = self.PROTOCOL.decode(response)
        if verbose:
            print(f"User balance for {product}: {data['user_balance']}")
        return data["user_balance"]

    def historical_order_books(self, product, history_length, verbose=True):
        """
        Returns the historical order books for a specific product.
        :param product: Product name
        :param history_length: Number of historical order books to return + 1 (current order book)
        :param verbose: If True, print the historical order books
        :return: historical order books
        """
        data = {"product": product, "history_len": history_length, "msg_type": "CaptureReportRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}",
                                json={"message": message, "msg_type": data["msg_type"]})
        response = self.parse_response(response)
        if response is None:
            return None
        response["msg_type"] = "CaptureReport"
        data = self.PROTOCOL.decode(response)
        if verbose:
            print(f"Historical order books for {product}:")
            for i, order_book in enumerate(data["history"]):
                order_book_dict = json.loads(order_book)  # Parse the order_book string to a dictionary
                print(f"Order book {i}:, timestamp: {order_book_dict['Timestamp']}")
                print("=====================================")
                self.display_order_book(order_book_dict, product=product)
                print()
        return data["history"]

    @staticmethod
    def display_order_book(order_book_data, aggregated=False, product=None):
        """
        Display the order book in a human-readable format. For debugging purposes.
        :param order_book_data: JSON with order book data
        :param aggregated: If True, display aggregated order book
        :param product: Product name
        :return: None
        """
        if product is not None:
            print(f"Order book for {product}:")
            print("=====================================")
        if order_book_data is None:
            print(f"\033[91mError: Order book for {product} not found.\033[0m")
            return

        bids_df = pd.DataFrame(order_book_data['Bids'])
        asks_df = pd.DataFrame(order_book_data['Asks'])

        if bids_df.empty and asks_df.empty:
            print("Order book is empty.")
            return

        if aggregated:
            print("Aggregated order book:")
            print("Bids DataFrame columns:", bids_df.columns)
            print("Asks DataFrame columns:", asks_df.columns)

            # Aggregate the order book
            if not bids_df.empty:
                bids_df = bids_df.groupby('Price', as_index=False).agg(
                    {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            if not asks_df.empty:
                asks_df = asks_df.groupby('Price', as_index=False).agg(
                    {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})

        # Concatenate bids and asks DataFrames side by side
        order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

        # Print the concatenated DataFrame
        print(order_book_df.fillna('').to_string(index=False))
