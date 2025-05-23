from collections import deque
import logging


class FIFOMatchingEngine:
    """
    First-In-First-Out matching engine to match buy and sell orders in an order book.
    """

    def __init__(self, order_book):
        """
        Initialize the matching engine with an order book.
        :param order_book: OrderBook object
        """
        self.order_book = order_book

    def match_order(self, new_order):
        """
        Match a new order with existing orders in the order book.
        :param new_order: Order object
        :return: True if the order was added to the order book, None if the order was fully matched and False if the order
        side is invalid
        """
        if new_order.side == 'buy':
            return self.match_buy_order(new_order)
        elif new_order.side == 'sell':
            return self.match_sell_order(new_order)
        else:
            logging.error(f"MATCH: Invalid order side: {new_order.side}")
            return False

    def match_buy_order(self, new_order):
        """
        Match a buy order with sell orders in the order book.
        :param new_order: Order object
        :return: True if the order was added to the order book, None if the order was fully matched
        """
        while new_order.quantity > 0 and self.order_book.asks:
            best_ask_price = self.order_book.get_best_ask()
            if new_order.price < best_ask_price:  # Price mismatch - too low
                break
            else:  # Match orders
                logging.info(f"MATCH: Matching buy order {new_order.id} with best ask {best_ask_price}")
                self.execute_trade(new_order, best_ask_price, 'sell')
        if new_order.quantity > 0:  # Add remaining order to the order book
            logging.info(f"MATCH: Order {new_order.id} wasn't fully matched, adding it to the order book.")
            self.order_book.add_order(new_order)
            return True
        return None

    def match_sell_order(self, new_order):
        """
        Match a sell order with buy orders in the order book.
        :param new_order: Order object
        :return: True if the order was added to the order book, None if the order was fully matched
        """
        while new_order.quantity > 0 and self.order_book.bids:
            best_bid_price = self.order_book.get_best_bid()
            if new_order.price > best_bid_price:
                break
            else:  # Match orders
                logging.info(f"MATCH: Matching sell order {new_order.id} with best bid {best_bid_price}")
                self.execute_trade(new_order, best_bid_price, 'buy')

        if new_order.quantity > 0:  # Add remaining order to the order book
            logging.info(f"MATCH: Order {new_order.id} wasn't fully matched, adding it to the order book.")
            self.order_book.add_order(new_order)
            return True
        return None

    def execute_trade(self, new_order, price, counter_side):
        """
        Execute a trade between a new order and an existing order at a given price level.
        :param new_order: Order object
        :param price: Price level
        :param counter_side: Counterparty side ('buy' or 'sell')
        :return: None
        """
        counter_order_queue = self.order_book.side_map[counter_side].get(price, deque())
        while new_order.quantity > 0 and counter_order_queue:
            best_counter_order = counter_order_queue[0]
            if best_counter_order.quantity > new_order.quantity:  # Full match
                best_counter_order.quantity -= new_order.quantity
                self.order_book.modify_user_balance(new_order.user, -price * new_order.quantity, -new_order.quantity,
                                                    side=counter_side)
                self.order_book.modify_user_balance(best_counter_order.user, price * new_order.quantity,
                                                    new_order.quantity, side=counter_side)
                self.order_book.modify_order_qty(best_counter_order.id, new_quantity=best_counter_order.quantity)
                new_order.quantity = 0
                logging.info(
                    f"MATCH: Full match between order {new_order.id} and order {best_counter_order.id} at price {price}")
            elif best_counter_order.quantity == new_order.quantity:  # Full match
                self.order_book.modify_user_balance(new_order.user, -price * best_counter_order.quantity,
                                                    -new_order.quantity, side=counter_side)
                self.order_book.modify_user_balance(best_counter_order.user, price * best_counter_order.quantity,
                                                    new_order.quantity,
                                                    side=counter_side)
                self.order_book.delete_best_order(counter_side, price)
                new_order.quantity = 0
                logging.info(
                    f"MATCH: Full match between order {new_order.id} and order {best_counter_order.id} at price {price}")
            else:  # Partial match
                new_order.quantity -= best_counter_order.quantity
                self.order_book.modify_user_balance(new_order.user, -price * best_counter_order.quantity,
                                                    -best_counter_order.quantity, side=counter_side)
                self.order_book.modify_user_balance(best_counter_order.user, price * best_counter_order.quantity,
                                                    best_counter_order.quantity,
                                                    side=counter_side)
                self.order_book.delete_best_order(counter_side, price)
                logging.info(
                    f"MATCH: Partial match between order {new_order.id} and order {best_counter_order.id} at price {price}")
