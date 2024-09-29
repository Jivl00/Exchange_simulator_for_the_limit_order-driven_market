from order_book import OrderBook
from order import Order

def main():
    # Initialize an empty order book
    order_book = OrderBook()
    order_book.add_order(Order(1, 0, 'buy', 100, 10.0))
    order_book.add_order(Order(2, 0, 'buy', 100, 10.0))
    order_book.display_order_book()

    order_book.modify_order_qty(1, new_quantity=50)
    order_book.display_order_book()

    order_book.modify_order_qty(1, new_quantity=150)
    order_book.modify_order(1, 2, 666.0, 6)
    order_book.display_order_book()

    best_order = order_book.get_best_bid()
    print(f"Best bid: {best_order}")



if __name__ == "__main__":
    main()