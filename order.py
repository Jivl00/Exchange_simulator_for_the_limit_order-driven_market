class Order:
    """A limit order to buy or sell a given quantity of shares at a specified price."""

    def __init__(self, id, timestamp, userID, side, quantity, price):
        self.id = id
        self.timestamp = timestamp
        self.user = userID
        self.side = side
        self.quantity = quantity
        self.price = price

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return f"Order({self.id}, {self.timestamp}, {self.user}, {self.side}, {self.quantity}, {self.price})"

    def __str__(self):
        return f"Order {self.id} ({self.side}) by {self.user} for {self.quantity} shares at ${self.price:.2f}"

    def _replace(self, **kwargs):
        """Replace attributes of the order."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self
