class User:
    def __init__(self, name, ID, budget):
        self.name = name
        self.user_ID = ID
        self.budget = budget
        self.post_buy_budget = budget


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

    def user_exists(self, user_ID):
        return user_ID in self.users
