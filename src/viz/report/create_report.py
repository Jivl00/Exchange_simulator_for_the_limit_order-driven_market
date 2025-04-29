import json
import pickle

import numpy as np
import pandas as pd
import plotly_resampler
from plotly_resampler import FigureResampler
import plotly.graph_objects as go


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


def plot_best_traders_interactive(users, timestamps, mid_prices, top_10):
    # Convert nanoseconds to datetime
    try:
        timestamps = pd.to_datetime(timestamps, unit='ns')
    except Exception as e:
        print(f"Error converting timestamps: {e}")
        return

    fig = FigureResampler(go.Figure(), default_downsampler=plotly_resampler.MinMaxLTTB(parallel=True))

    user_balances = {}
    for user, data in users.items():
        if user in top_10["User"].values and len(data["balance"]) > 0:
            volume = np.array(data["volume"])
            balance = np.array(data["balance"]) + volume * mid_prices[-1]
            # Pad the balance with 0 in the beginning to match the length of timestamps
            padding = np.zeros(len(timestamps) - len(balance))  # Create padding as a numpy array
            balance = np.concatenate((padding, balance))  # Concatenate padding and balance
            user_balances[user] = balance

    # Add user balances to the plot
    for user in top_10["User"].values:
        user_name = f"{user[:4]}...{user[-4:]}"
        if user in user_balances:
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=user_balances[user],
                mode='lines',
                name=user_name,
                # name=users[user]["name"],
                yaxis="y1"
            ))

    # Add mid prices to the plot
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=mid_prices,
        mode='lines',
        name="Mid Price",
        line=dict(color='black'),
        opacity=0.5,
        yaxis="y2"
    ))

    # Update layout for dual y-axes
    fig.update_layout(
        title=dict(
            text="Balance of Best Traders Over Time",
            y=1,  # Move the title higher
            pad=dict(t=5),  # Add padding to the title

        ),
        xaxis=dict(title="Timestamp"),
        yaxis=dict(title="Balance", side="left"),
        yaxis2=dict(title="Mid Price", overlaying="y", side="right"),
        legend=dict(orientation="h", x=0.5, y=1.4, xanchor="center"),
        margin=dict(l=50, r=50, t=170, b=50),
        height=500, width=800,
    )

    for trace in fig.data:
        trace.name = trace.name.split("~")[0].strip()
        trace.name = trace.name.replace("[R]", "").strip()

    # Update layout for font size
    fig.update_layout(
        title=dict(
            text="Balance of Best Traders Over Time",
            y=1,
            font=dict(size=20)  # Increase title font size
        ),
        xaxis=dict(
            title="Timestamp",
            titlefont=dict(size=16),  # Increase x-axis title font size
            tickfont=dict(size=14)  # Increase x-axis tick font size
        ),
        yaxis=dict(
            title="Balance",
            titlefont=dict(size=16),  # Increase y-axis title font size
            tickfont=dict(size=14)  # Increase y-axis tick font size
        ),
        yaxis2=dict(
            title="Mid Price",
            titlefont=dict(size=16),  # Increase secondary y-axis title font size
            tickfont=dict(size=14)  # Increase secondary y-axis tick font size
        ),
        legend=dict(
            font=dict(size=14)  # Increase legend font size
        ),
        margin=dict(l=50, r=50, t=170, b=50),
        height=500, width=800,
    )

    # Show the interactive plot
    fig.show()
    # Save the plot as a pdf
    fig.write_image("best_traders_plot.pdf", format="pdf", engine="kaleido")
    # Save the interactive plot as an HTML file
    fig.write_html("best_traders_plot.html")
    # Save the interactive plot as an png file
    fig.write_image("best_traders_plot.png", format="png", engine="kaleido")

