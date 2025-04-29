class User:
    """
    Class representing a user in the system.
    """
    def __init__(self, name, ID, budget):
        """
        Initialize a user with a name, ID, and budget.
        :param name: Name of the user
        :param ID: Unique identifier for the user
        :param budget: Initial budget for the user
        """
        self.name = name
        self.user_ID = ID
        self.budget = budget
        self.num_orders = 0
        self.post_buy_budget = budget

    def __str__(self):
        return f"User {self.name} ({self.user_ID}) with budget {self.budget} sent {self.num_orders} orders."


class UserManager:
    """
    Class to manage users in the system.
    """
    def __init__(self):
        """
        Initialize the UserManager with an empty user list.
        """
        self.users = {}

        # Set up initial users here - no UUIDs will be used for the initial users -> better for testing
        # self.add_user("market_maker", "market_maker", 0)
        # self.add_user("liquidity_generator", "liquidity_generator", 0)

    def add_user(self, name, ID, budget):
        """
        Add a new user to the system.
        :param name: Name of the user
        :param ID: Unique identifier for the user
        :param budget: Initial budget for the user
        """
        self.users[ID] = User(name, ID, budget)

    def set_user_budget(self, user_ID, budget):
        """
        Set the budget for a user.
        :param user_ID: Unique identifier for the user
        :param budget: New budget for the user
        """
        self.users[user_ID].budget = budget

    def increment_user_orders_counter(self, user_ID):
        """
        Increment the number of orders sent by a user.
        :param user_ID: Unique identifier for the user
        """
        self.users[user_ID].num_orders += 1

    def user_exists(self, user_ID):
        """
        Check if a user exists in the system.
        :param user_ID: Unique identifier for the user
        :return: True if the user exists, False otherwise
        """
        return user_ID in self.users

    def user_name_exists(self, user_name):
        """
        Check if a user name exists in the system.
        :param user_name: Name of the user
        :return: True if the user name exists, False otherwise
        """
        user_id = next((user.user_ID for user in self.users.values() if user.name == user_name), None)
        return user_id
