import json
import pickle

import pandas as pd


def pickle_load(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)

def display_order_book(order_book_data, aggregated=False, product=None):
    """
    Display the order book in a human-readable format. For debugging purposes.
    :param order_book_data: JSON with order book data
    :param aggregated: If True, display aggregated order book
    :param product: Product name
    :return: None
    """
    if product is not None:
        print(f"Order book for {product}:")
        print("=====================================")
    if order_book_data is None:
        print(f"\033[91mError: Order book for {product} not found.\033[0m")
        return

    bids_df = pd.DataFrame(order_book_data['Bids'])
    asks_df = pd.DataFrame(order_book_data['Asks'])

    if bids_df.empty and asks_df.empty:
        print("Order book is empty.")
        return

    if aggregated:
        print("Aggregated order book:")
        print("Bids DataFrame columns:", bids_df.columns)
        print("Asks DataFrame columns:", asks_df.columns)

        # Aggregate the order book
        if not bids_df.empty:
            bids_df = bids_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
        if not asks_df.empty:
            asks_df = asks_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})

    # Concatenate bids and asks DataFrames side by side
    order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

    # Print the concatenated DataFrame
    print(order_book_df.fillna('').to_string(index=False))

if __name__ == '__main__':
    file_path = '../data/2025-04-04_20-52-09-server_data.pickle'
    data = pickle_load(file_path)
    for product, order_books in data.items():
        users = {}
        timestamps = []
        for user, user_data in order_books["users"].items():
            users[user] = {
                "name": user_data.name,
                "budget": user_data.budget,
                "balance": [],
                "volume": [],
                "num_orders": 0,
            }
        for order_book in order_books["order_books"]:
            order_book = json.loads(order_book)
            for user, user_data in order_book["UserBalance"].items():
                users[user]["balance"].append(user_data["balance"])
                users[user]["volume"].append(user_data["volume"])
            timestamps.append(order_book["Timestamp"])
            bids_df = pd.DataFrame(order_book['Bids'])
            asks_df = pd.DataFrame(order_book['Asks'])
            for df in [bids_df, asks_df]:
                for _, row in df.iterrows():
                    user = row['User']
                    if user in users:
                        users[user]["num_orders"] += 1
    print("Users:")
    for user, user_data in users.items():
        print(f"User {user}:")
        print(f"  Name: {user_data['name']}")
        print(f"  Budget: {user_data['budget']}")
        print(f"  Balance: {user_data['balance']}")
        print(f"  Volume: {user_data['volume']}")
        print(f"  Orders: {user_data['num_orders']}")
