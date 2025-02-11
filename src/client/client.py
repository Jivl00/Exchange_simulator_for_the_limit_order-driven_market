import requests
import pandas as pd
from src.protocols.FIXProtocol import FIXProtocol


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


    def order_stats(self, ID, product):
        """
        Request order status from the server.
        :param ID: Order ID
        :param product: Product name
        :return: JSON with order details (id, timestamp, user, side, quantity, price) if found, None otherwise
        """
        data = {"ID": ID, "product": product, "msg_type": "OrderStatusRequest"}
        message = self.PROTOCOL.encode(data)

        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        response = response.json()
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
        data = {"order": order, "product": product, "msg_type": "NewOrderSingle"}
        message = self.PROTOCOL.encode(data)

        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        response = response.json()
        response["msg_type"] = "ExecutionReport"
        response_data = self.PROTOCOL.decode(response)
        if response_data["status"] is False:
            print("\033[91mError: Order put failed.\033[0m")  # Print in red

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

        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        response = response.json()
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
        response = requests.post(f"{self.BASE_URL}/{self.TRADING_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        response = response.json()
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
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        order_book_data = response.json()
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
        response = requests.get(f"{self.BASE_URL}/{self.QUOTE_SESSION}", json={"message": message, "msg_type": data["msg_type"]})
        response = response.json()
        response["msg_type"] = "UserOrderStatus"
        data = self.PROTOCOL.decode(response)
        data = data["user_orders"]
        print(pd.DataFrame(data).T)
        return data

    @staticmethod
    def display_order_book(order_book_data, product=None):
        """
        Display the order book in a human-readable format. For debugging purposes.
        :param order_book_data: JSON with order book data
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

        # Concatenate bids and asks DataFrames side by side
        order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

        # Print the concatenated DataFrame
        print(order_book_df.fillna('').to_string(index=False))
