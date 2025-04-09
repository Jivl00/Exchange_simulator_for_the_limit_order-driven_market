class User:
    def __init__(self, name, ID, budget):
        self.name = name
        self.user_ID = ID
        self.budget = budget
        self.num_orders = 0
        self.post_buy_budget = budget

    def __str__(self):
        return f"User {self.name} ({self.user_ID}) with budget {self.budget} sent {self.num_orders} orders."


class UserManager:
    def __init__(self):
        self.users = {}

        # Add market maker and liquidity generator users
        self.add_user("market_maker", "market_maker", 0)
        self.add_user("liquidity_generator", "liquidity_generator", 0)

    def add_user(self, name, ID, budget):
        self.users[ID] = User(name, ID, budget)

    def set_user_budget(self, user_ID, budget):
        self.users[user_ID].budget = budget

    def increment_user_orders_counter(self, user_ID):
        self.users[user_ID].num_orders += 1

    def user_exists(self, user_ID):
        return user_ID in self.users

    def user_name_exists(self, user_name):
        user_id = next((user.user_ID for user in self.users.values() if user.name == user_name), None)
        return user_id
