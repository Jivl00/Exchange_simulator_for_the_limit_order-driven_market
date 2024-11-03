from matching_engine import FIFOMatchingEngine
from order_book import OrderBook
from order import Order
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    # Initialize an empty order book
    order_book = OrderBook()
    order_book.add_order(Order(1, 0, 'pepa', 'buy', 100, 20.0))
    order_book.add_order(Order(21, 1, 'pepa', 'buy', 100, 10.0))
    order_book.add_order(Order(22, 2, 'pepa', 'buy', 100, 10.0))
    order_book.add_order(Order(23, 3, 'pepa', 'buy', 100, 10.0))

    order_book.add_order(Order(2, 1, 'pepa', 'sell', 50, 30.0))
    order_book.add_order(Order(2.1, 2, 'pepa', 'sell', 100, 30.0))
    order_book.add_order(Order(3, 2, 'pepa', 'sell', 100, 25.0))
    order_book.display_order_book()
    print(order_book.get_orders_by_user('pepa'))

    order_book.modify_order_qty(1, new_quantity=50)
    order_book.display_order_book()

    order_book.modify_order_qty(1, new_quantity=150)
    order_book.modify_order(1, 2, 5.0, 6)
    order_book.display_order_book()

    best_order = order_book.get_best_bid()
    print(f"Best bid: {best_order}")

    # Initialize a FIFO matching engine
    fifo_matching_engine = FIFOMatchingEngine(order_book)
    fifo_matching_engine.match_order(Order(4, 4, 'karel','buy', 310, 30.0))
    order_book.display_order_book()

    fifo_matching_engine.match_order(Order(5, 5, 'karel', 'sell', 100, 10.0))
    order_book.display_order_book()

    fifo_matching_engine.match_order(Order(55, 5, 'karel', 'sell', 150, 10.0))
    order_book.display_order_book()

    print(order_book.jsonify_order_book())


if __name__ == "__main__":
    main()
