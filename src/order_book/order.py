class Order:
    """
    A limit order to buy or sell a given quantity of shares at a specified price.
    """

    def __init__(self, id, timestamp, userID, side, quantity, price):
        """
        Initialize an order.
        :param id: unique order ID
        :param timestamp: time of order creation - nanoseconds since epoch
        :param userID: user ID
        :param side: 'buy' or 'sell'
        :param quantity: number of shares
        :param price: price per share
        """
        self.id = id
        self.timestamp = timestamp
        self.user = userID
        self.side = side
        self.quantity = quantity
        self.price = round(price, 2)

    def __eq__(self, other):
        return self.id == other.id

    def __json__(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "user": self.user,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price
        }

    def __repr__(self):
        return f"Order({self.id}, {self.timestamp}, {self.user}, {self.side}, {self.quantity}, {self.price})"

    def __str__(self):
        return f"Order {self.id} ({self.side}) by {self.user} for {self.quantity} shares at ${self.price:.2f}"

    def _replace(self, **kwargs):
        """
        Replace attributes of the order.
        :param kwargs: new attributes
        :return: updated order
        """
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self
