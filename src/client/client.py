import requests
import pandas as pd
from src.protocols.fix import FIXProtocol


class Client:
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
        self.BASE_URL = f"{config['HOST']}:{config['PORT']}"
        self.TRADING_SESSION = config["TRADING_SESSION"]
        self.QUOTE_SESSION = config["QUOTE_SESSION"]

        self.PROTOCOL = FIXProtocol(sender, target)
        self.parser = self.PROTOCOL.parser

    def parse_message(self, msg):
        """
        Parse the incoming FIX message.
        :param msg: FIX message
        :return: Decoded message
        """
        message = msg['message']
        self.parser.append_buffer(message)
        message = self.parser.get_message()
        print(f"R>: {message}")
        return message

    def order_stats(self, ID):
        """
        Request order status from the server.
        :param ID: Order ID
        :return: JSON with order details (id, timestamp, user, side, quantity, price) if found, None otherwise
        """
        data = {"ID": ID, "msg_type": "OrderStatusRequest"}
        message = self.PROTOCOL.encode(data)

        response = requests.get(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message})

        response_data = response.json()
        message = self.parse_message(response_data)
        if message.get(39).decode() != '8':  # OrderStatus != Rejected
            order = {'id': message.get(37).decode(), 'side': 'buy' if message.get(54).decode() == '1' else 'sell',
                     'quantity': int(message.get(151).decode()), 'price': float(message.get(44).decode())}
            return order
        return None

    def put_order(self, order):
        """
        Send a new order request to the server.
        :param order: Dictionary containing order details
        :return: Order ID if not fully filled, None otherwise
        """
        data = {"order": order, "msg_type": "NewOrderSingle"}
        message = self.PROTOCOL.encode(data)
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message})
        print(response.json())
        return response.json()

    def delete_order(self, ID):
        """
        Send an order cancel request to the FIX server.
        :param ID: Order ID
        :return: None
        """
        data = {"ID": ID, "msg_type": "OrderCancelRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message})
        print(response.json())

    def modify_order_qty(self, ID, quantity):
        """
        Modify order quantity - only decrease is allowed.
        :param ID: Order ID
        :param quantity: New quantity
        :return: None
        """
        data = {"ID": ID, "quantity": quantity, "msg_type": "OrderModifyRequestQty"}
        message = self.PROTOCOL.encode(data)
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message})
        print(response.json())

    def modify_order(self, ID, new_price=None, new_quantity=None):
        """
        Modify an existing order - price and/or quantity.
        :param ID: Order ID
        :param new_price: New price (or None)
        :param new_quantity: New quantity (or None)
        :return: None
        """
        order = self.order_stats(ID)
        if order is None:
            print(f"Order {ID} not found.")
            return
        self.delete_order(ID)
        if new_price is not None:
            order['price'] = new_price
        if new_quantity is not None:
            order['quantity'] = new_quantity
        return self.put_order(order)

    def order_book_request(self, depth=0):
        """
        Returns the order book from the FIX server.
        :param depth: Market depth (0 = full book)
        :return: JSON with order book data
        """
        data = {"depth": depth, "msg_type": "MarketDataRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}", json={"message": message})
        order_book_data = response.json()

        return order_book_data

    def list_user_orders(self):
        """
        Returns a list of orders for a specific user.
        :return: JSON with order data
        """
        data = {"msg_type": "UserOrderStatusRequest"}
        message = self.PROTOCOL.encode(data)
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}", json={"message": message})
        print(response.json())

    def display_order_book(self, order_book_data):
        """
        Display the order book in a human-readable format. For debugging purposes.
        :param order_book_data: JSON with order book data
        :return: None
        """
        bids_df = pd.DataFrame(order_book_data['Bids'])
        asks_df = pd.DataFrame(order_book_data['Asks'])

        # Concatenate bids and asks DataFrames side by side
        order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

        # Print the concatenated DataFrame
        print(order_book_df.fillna('').to_string(index=False))
