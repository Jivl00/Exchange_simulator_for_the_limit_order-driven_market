import json
import pickle

import numpy as np
import pandas as pd


def pickle_load(file_path):
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def extract_user_data(order_books, users, timestamps, mid_prices):

    for user, user_data in order_books["users"].items():
        if user not in users:
            users[user] = {}
        users[user]["name"] = user_data.name
        users[user]["budget"] = user_data.budget
        users[user]["num_orders"] = user_data.num_orders

        if "balance" not in users[user]:
            users[user]["balance"] = []
            users[user]["volume"] = []

    threshold = "2025-04-21T13:13:00.000000Z"
    threshold_ns = pd.to_datetime(threshold).value

    for order_book in order_books["order_books"]:
        ob = json.loads(order_book)

        # if int(ob["Timestamp"]) > int(threshold_ns):
        #     print(f"Skipping timestamp {ob['Timestamp']} as it is before the threshold.")
        #     continue

        timestamps.append(ob["Timestamp"])

        bids_df = pd.DataFrame(ob["Bids"])
        asks_df = pd.DataFrame(ob["Asks"])
        if not bids_df.empty and not asks_df.empty:
            mid_price = (bids_df['Price'].iloc[0] + asks_df['Price'].iloc[0]) / 2
            mid_prices.append(mid_price)
        else:
            mid_prices.append(None)

        for user, data in ob["UserBalance"].items():
            users[user]["balance"].append(data["balance"])
            users[user]["volume"].append(data["volume"])

    return users, timestamps, mid_prices


def compute_statistics(users, mid_prices, initial_budget=10000):
    stats = []
    stock_income = 0
    for user, data in users.items():
        if user in ["market_maker", "liquidity_generator"]:
            continue
        stock_income += (initial_budget - data["budget"])

        final_balance = data["budget"]
        volume_series = data["volume"]
        balance_series = data["balance"]

        if balance_series:
            final_balance += balance_series[-1]
            if mid_prices and mid_prices[-1]:
                final_balance += volume_series[-1] * mid_prices[-1]
                # final_balance += volume_series[-1] * 114.125

        pnl = final_balance - initial_budget
        avg_balance = np.mean(balance_series) if balance_series else 0

        stats.append({
            "User": user, # Uncomment if you want to include user ID
            "Name": data["name"],
            "FinalBalance": final_balance,
            "Return (%)": (pnl / initial_budget) * 100 if initial_budget else 0,
            "AvgVolumePerStep": np.mean(volume_series) if volume_series else 0,
            "MaxVolume": max(volume_series, default=0),
            "AvgBalance": avg_balance,
            "NumOrders": data["num_orders"],
        })
    stats_df = pd.DataFrame(stats).sort_values(by="FinalBalance", ascending=False)
    return stats_df, stock_income

def plot_best_traders(users, timestamps, mid_prices, top_10):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    # Convert nanoseconds to datetime
    try:
        timestamps = pd.to_datetime(timestamps, unit='ns')
    except Exception as e:
        print(f"Error converting timestamps: {e}")
        return
    fig, ax = plt.subplots(figsize=(12, 6))

    # Primary y-axis for user balances
    for user, data in users.items():
        if user not in top_10["User"].values:
            continue
        if len(data["balance"]) > 0:
            # padd the balance with 0 in the beginning to match the length of timestamps
            balance = data["balance"]
            balance = [0] * (len(timestamps) - len(balance)) + balance
            ax.plot(timestamps, balance, label=data["name"])

    # Secondary y-axis for mid prices
    ax2 = ax.twinx()
    ax2.plot(timestamps, mid_prices, label="Mid Price", color='black', linestyle='--')
    ax2.set_ylabel("Mid Price", color='black')
    ax2.tick_params(axis='y', labelcolor='black')

    # Formatting the x-axis
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)

    # Labels and title
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Balance")
    ax.set_title("Balance of Best Traders Over Time")

    # Legends
    lines_1, labels_1 = ax.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper left")

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    file_paths = ['../data/2025-04-17_15-53-24-server_data.pickle', '../data/2025-04-17_15-58-57-server_data.pickle']
    # file_paths = ['../data/2025-04-17_15-58-57-server_data.pickle']
    users = {}
    timestamps = []
    mid_prices = []
    for file_path in file_paths:
        print(f"Processing file: {file_path}")
        data = pickle_load(file_path)
        for _, order_books in data.items():
            extract_user_data(order_books, users, timestamps, mid_prices)
    stats_df, stock_income = compute_statistics(users, mid_prices)
    print(stats_df.to_string(index=False, justify='rigth', float_format='%.2f'))
    print(f"  Stock fee income: {stock_income}")
    top_10 = stats_df.head(10)
    plot_best_traders(users, timestamps, mid_prices, top_10)
