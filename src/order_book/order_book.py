import json
from collections import defaultdict
import pandas as pd
from collections import deque
from sortedcontainers import SortedDict
import logging
import copy


class OrderBook:
    """
    Order book class to store and manage orders. Stores current state of the order book.
    """

    def __init__(self):
        """
        Initialize an empty order book.
        """
        self.bids = SortedDict()  # Key: Price, Value: deque of Orders (bid side)
        self.asks = SortedDict()  # Key: Price, Value: deque of Orders (ask side)
        self.order_map = {}  # Key: Order ID, Value: (Order, Price level in bids/asks)

        self.side_map = {  # Map side to price level
            'buy': self.bids,
            'sell': self.asks
        }

        self.user_balance = defaultdict(lambda: {'balance': 0, 'volume': 0})  # Key: User ID
        self.timestamp = 0 # Timestamp in which the order book was last saved

    def copy(self):
        return copy.deepcopy(self)

    def reset_book(self):
        """
        Reset the order book to an empty state.
        """
        self.bids = SortedDict()
        self.asks = SortedDict()
        self.order_map = {}

        self.side_map = {
            'buy': self.bids,
            'sell': self.asks
        }

        self.user_balance = defaultdict(lambda: {'balance': 0, 'volume': 0})

        logging.debug("ORDERBOOK: Order book reset.")

    def get_order_by_id(self, order_id):
        """
        Get an order by its ID.
        :param order_id: Order ID
        :return: Order object or None if not found
        """
        return self.order_map.get(order_id, None)  # Return None if order_id not found

    def add_order(self, order):
        """
        Add a new order to the order book.
        :param order: Order object
        :return: None
        """
        price_level = self.side_map[order.side]  # Bids or asks
        if order.price not in price_level:
            price_level[order.price] = deque()  # Initialize deque for the price level
        price_level[order.price].append(order)

        # Keep track of orders
        self.order_map[order.id] = order

        logging.debug(
            f"ORDERBOOK: Added Order {order.id} ({order.side}): {order.quantity} shares at ${order.price:.2f}")

    def delete_order(self, order_id):
        """
        Delete an order from the order book.
        :param order_id: Order ID
        :return: True if the order was deleted, False otherwise
        """
        if order_id not in self.order_map:
            logging.warning(f"ORDERBOOK: Order {order_id} not found in the order book.")
            return False
        # Delete the order from the order map
        order = self.order_map[order_id]
        del self.order_map[order_id]

        # Delete the order from the bids or asks
        price_level = self.side_map[order.side]
        price_level[order.price].remove(order)
        if not price_level[order.price]:  # Delete the price level if it's empty - no orders at that price
            del price_level[order.price]

        logging.debug(
            f"ORDERBOOK: Deleted Order {order.id} ({order.side}): {order.quantity} shares at ${order.price:.2f}")
        return True

    def delete_best_order(self, side, price):
        """
        Delete the best order from the order book - using .popleft() method. For trading purposes only.
        :param side: Order side ('buy' or 'sell')
        :param price: Order price
        :return: None
        """
        if price not in self.side_map[side]:
            logging.warning(f"ORDERBOOK: No orders found at price {price} on the {side} side.")
            return
        order = self.side_map[side][price][0]
        del self.order_map[order.id]

        self.side_map[side][price].popleft()
        if not self.side_map[side][price]:  # Delete the price level if it's empty - no orders at that price
            del self.side_map[side][price]

    def modify_order_qty(self, order_id, new_quantity=None):
        """
        Modify an existing order in the order book - quantity decrease only.

        This transaction does not make the order lose its price-time
        priority in the queue, if the price is not modified and the
        quantity is decreased.

        For quantity increase or price modification, delete the order
        and re-added it to the order book - modify_order() method.

        :param order_id: Order ID
        :param new_quantity: New quantity (must be less than or equal to the original quantity)
        :return: True if the order was modified, False otherwise
        """
        if order_id not in self.order_map:
            logging.warning(f"ORDERBOOK: Order {order_id} not found in the order book.")
            return False

        order = self.order_map[order_id]

        if new_quantity is not None and new_quantity <= order.quantity:
            logging.debug(
                f"ORDERBOOK: Decreasing the quantity of Order {order_id} from {order.quantity} to {new_quantity}.")
            order.quantity = new_quantity
        else:
            logging.warning(f"ORDERBOOK: Quantity increase or price modification not supported in modify_order_qty().")
            return False
        return True

    def modify_order(self, order_id, timestamp, new_price=None, new_quantity=None):
        """
        Modify an existing order in the order book.

        This transaction makes the order lose its price-time priority
        in the queue. The order is deleted and re-added to the order book.

        For quantity decrease only, use modify_order_qty() method which
        preserves the price-time priority.

        :param order_id: Order ID
        :param timestamp: Timestamp of the modification
        :param new_price: New price (or None)
        :param new_quantity: New quantity (or None)
        :return: None
        """
        if order_id not in self.order_map:
            logging.warning(f"ORDERBOOK: Order {order_id} not found in the order book.")
            return

        order = self.order_map[order_id]

        # Delete the order
        self.delete_order(order_id)
        # Modify the order
        if new_price is not None:
            order.price = round(new_price, 2)
        if new_quantity is not None:
            order.quantity = new_quantity
        # Re-add the order
        self.add_order(order._replace(timestamp=timestamp))

        logging.debug(
            f"ORDERBOOK: Modified Order {order_id} ({order.side}): {order.quantity} shares at ${order.price:.2f}")

    def modify_user_balance(self, user_id, amount, volume, side):
        """
        Modify the balance of a user.
        :param user_id: User ID
        :param amount: Amount to modify the balance by
        :param volume: Volume to modify the balance by
        :param side: Side of the transaction ('buy' or 'sell')
        :return: None
        """
        if side == 'buy':
            self.user_balance[user_id]['balance'] -= amount
            self.user_balance[user_id]['volume'] += volume
        elif side == 'sell':
            self.user_balance[user_id]['balance'] += amount
            self.user_balance[user_id]['volume'] -= volume

    def get_best_bid(self):
        """
        Return the best bid price. The best bid price is the highest price in the bids.
        :return: Best bid price or None if no bids
        """
        if not self.bids:
            return None
        best_price = self.bids.peekitem(-1)[0]  # get max price

        return best_price

    def get_best_ask(self):
        """
        Get the best ask price. The best ask price is the lowest price in the asks.
        :return: Best ask price or None if no asks
        """
        if not self.asks:
            return None
        best_price = self.asks.peekitem(0)[0]  # get min price
        return best_price

    def get_orders_by_user(self, user_id):
        """
        Get all orders by a user.
        :param user_id: User ID
        :return: List of orders by the user
        """
        user_orders = []
        for order in self.order_map.values():
            if order.user == user_id:
                user_orders.append(order)
        return user_orders

    def get_user_balance(self, user_id):
        """
        Get the balance of a user.
        :param user_id: User ID
        :return: Balance of the user
        """
        return self.user_balance.get(user_id, {'balance': 0, 'volume': 0}) # Return 0 if user not found

    """
    -------------------------------
    All display methods below are for non-aggregated order book display.
    -------------------------------
    """

    def jsonify_order_book(self, depth=-1):
        """
        Display the order book with a specified depth.
        :param depth: Depth of the order book (N price tiers of data) (default: -1 for full order book)
        :return: JSON string of the order book
        """
        bids = []
        asks = []

        # Get the best (depth) bid prices
        for price, orders in reversed(self.bids.items()):
            for order in orders:
                bids.append({'ID': order.id, 'User': order.user, 'Quantity': order.quantity, 'Price': price})
            if 0 < depth <= len(bids):
                break

        # Get the best (depth) ask prices
        for price, orders in self.asks.items():
            for order in orders:
                asks.append({'ID': order.id, 'User': order.user, 'Quantity': order.quantity, 'Price': price})
            if 0 < depth <= len(asks):
                break

        order_book_data = {
            'Bids': bids,
            'Asks': asks,
            'Timestamp': self.timestamp
        }

        return json.dumps(order_book_data)


"""
-------------------------------
Might be useful for debugging
-------------------------------
"""


def display_order_book(self):
    """Display the order book."""
    bids_df = pd.DataFrame(columns=['ID', 'User', 'Quantity', 'Price'])
    asks_df = pd.DataFrame(columns=['ID', 'User', 'Quantity', 'Price'])
    for price, orders in self.bids.items():
        for order in orders:
            bids_df = pd.concat(
                [bids_df, pd.DataFrame([{'ID': order.id, 'User': order.user, 'Quantity': order.quantity,
                                         'Price': price}])], ignore_index=True)
    for price, orders in self.asks.items():
        for order in orders:
            asks_df = pd.concat(
                [asks_df, pd.DataFrame([{'ID': order.id, 'User': order.user, 'Quantity': order.quantity,
                                         'Price': price}])], ignore_index=True)

    # Concatenate bids and asks DataFrames side by side
    order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

    # Print the concatenated DataFrame
    # print(order_book_df.fillna('').to_markdown(index=False))
    print(order_book_df.fillna('').to_string(index=False))
