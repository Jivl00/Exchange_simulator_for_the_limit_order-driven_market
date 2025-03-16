

class User:
    def __init__(self, name, ID, budget):
        self.name = name
        self.user_ID = ID
        self.budget = budget
        self.post_buy_budget = budget

class UserManager:
    def __init__(self):
        self.users = {}

    def add_user(self, name, ID, budget):
        self.users[ID] = User(name, ID, budget)

    def user_exists(self, user_ID):
        return user_ID in self.users


