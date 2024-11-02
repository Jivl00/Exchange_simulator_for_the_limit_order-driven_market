import json

import pandas as pd
from collections import deque
import logging


class OrderBook:
    def __init__(self):
        self.bids = {}  # Key: Price, Value: deque of Orders (bid side)
        self.asks = {}  # Key: Price, Value: deque of Orders (ask side)
        self.order_map = {}  # Key: Order ID, Value: (Order, Price level in bids/asks)

        self.side_map = {  # Map side to price level
            'buy': self.bids,
            'sell': self.asks
        }

    def reset_book(self):
        """Reset the order book to an empty state."""
        self.bids = {}
        self.asks = {}
        self.order_map = {}

        self.side_map = {
            'buy': self.bids,
            'sell': self.asks
        }
        logging.debug("ORDERBOOK: Order book reset.")

    def get_order_by_id(self, order_id):
        """Get an order by its ID."""
        return self.order_map.get(order_id, None) # Return None if order_id not found

    def add_order(self, order):
        """Add a new order to the order book."""
        price_level = self.side_map[order.side]  # Bids or asks
        if order.price not in price_level:
            price_level[order.price] = deque()  # Initialize deque for the price level
        price_level[order.price].append(order)

        # Keep track of orders
        self.order_map[order.id] = order

        logging.debug(
            f"ORDERBOOK: Added Order {order.id} ({order.side}): {order.quantity} shares at ${order.price:.2f}")

    def delete_order(self, order_id):
        """Delete an order from the order book."""
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
        """Delete the best order from the order book - using .popleft() method."""
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

    # def modify_order(self, order_id, timestamp, new_price=None, new_quantity=None):
    #     """
    #     Modify an existing order in the order book.
    #
    #     This transaction makes the order lose its price-time priority
    #     in the queue. The order is deleted and re-added to the order book.
    #
    #     For quantity decrease only, use modify_order_qty() method which
    #     preserves the price-time priority.
    #     """
    #     if order_id not in self.order_map:
    #         logging.warning(f"ORDERBOOK: Order {order_id} not found in the order book.")
    #         return
    #
    #     order = self.order_map[order_id]
    #
    #     # Delete the order
    #     self.delete_order(order_id)
    #     # Modify the order
    #     if new_price is not None:
    #         order.price = new_price
    #     if new_quantity is not None:
    #         order.quantity = new_quantity
    #     # Re-add the order
    #     self.add_order(order._replace(timestamp=timestamp))
    #
    #     logging.debug(
    #         f"ORDERBOOK: Modified Order {order_id} ({order.side}): {order.quantity} shares at ${order.price:.2f}")

    def get_best_bid(self):
        """Return the best bid price."""
        if not self.bids:
            return None
        best_price = max(self.bids.keys())

        return best_price

    def get_best_ask(self):
        """Get the best ask price."""
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        return best_price

    def get_order_by_user(self, user_id):
        """Get all orders by a user."""
        user_orders = []
        for order in self.order_map.values():
            if order.user == user_id:
                user_orders.append(order)
        return user_orders

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

    def jsonify_order_book(self):
        """Display the order book."""
        bids = []
        asks = []
        for price, orders in self.bids.items():
            for order in orders:
                bids.append({'ID': order.id, 'User': order.user, 'Quantity': order.quantity, 'Price': price})
        for price, orders in self.asks.items():
            for order in orders:
                asks.append({'ID': order.id, 'User': order.user, 'Quantity': order.quantity, 'Price': price})

        order_book_data = {
            'Bids': bids,
            'Asks': asks
        }

        return json.dumps(order_book_data)
