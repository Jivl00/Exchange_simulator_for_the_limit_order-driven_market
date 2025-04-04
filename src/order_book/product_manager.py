from order_book.matching_engine import FIFOMatchingEngine
from order_book.order_book import OrderBook


class TradingProductManager:
    def __init__(self, products):
        self.order_books = {product: OrderBook() for product in products}
        self.historical_order_books = {product: [] for product in products}
        self.matching_engines = {product: FIFOMatchingEngine(self.order_books[product]) for product in products}

    def set_order_book(self, product, order_book):
        if product not in self.order_books:
            raise ValueError(f"Product {product} not found")
        self.order_books[product] = order_book
        self.matching_engines[product] = FIFOMatchingEngine(order_book)

    def get_order_book(self, product, save_history=True, timestamp=None):
        if save_history and timestamp is None:
            raise ValueError("Timestamp must be provided if save_history is True")
        if save_history:
            self.order_books[product].timestamp = self.order_books[product].timestamp + 1
            self.historical_order_books[product].append(self.order_books[product].copy().jsonify_order_book())
        return self.order_books.get(product)

    def get_matching_engine(self, product, timestamp):
        self.order_books[product].timestamp = timestamp
        self.historical_order_books[product].append(self.order_books[product].copy().jsonify_order_book())
        return self.matching_engines.get(product)

    def get_historical_order_books(self, product, history_length):
        if history_length == -1:
            return self.historical_order_books[product]
        return self.historical_order_books[product][-history_length:]