import requests
import json
import pandas as pd

BASE_URL = "http://127.0.0.1:8888"

def add_order(order):
    response = requests.post(f"{BASE_URL}/add_order", json=order)
    print(response.json())

def modify_order_qty(order_id, new_quantity):
    data = {
        "order_id": order_id,
        "new_quantity": new_quantity
    }
    response = requests.post(f"{BASE_URL}/modify_order_qty", json=data)
    print(response.json())

def match_order(order):
    response = requests.post(f"{BASE_URL}/match_order", json=order)
    print(response.json())

def display_order_book():
    response = requests.get(f"{BASE_URL}/display_order_book")
    order_book_data = response.json()

    bids_df = pd.DataFrame(order_book_data['Bids'])
    asks_df = pd.DataFrame(order_book_data['Asks'])

    # Concatenate bids and asks DataFrames side by side
    order_book_df = pd.concat([bids_df, asks_df], axis=1, keys=['Bids', 'Asks'])

    # Print the concatenated DataFrame
    print(order_book_df.fillna('').to_string(index=False))




if __name__ == "__main__":
    # Example usage
    add_order({"id": 1, "timestamp": 0, "side": "buy", "quantity": 100, "price": 20.0})
    add_order({"id": 2, "timestamp": 1, "side": "sell", "quantity": 50, "price": 30.0})
    display_order_book()
    modify_order_qty(1, 50)
    display_order_book()
    match_order({"id": 3, "timestamp": 2, "side": "buy", "quantity": 60, "price": 30.0})
    display_order_book()

    while True:
        print("1. Add order")
        print("2. Modify order quantity")
        print("3. Match order")
        print("4. Display order book")
        print("5. Exit")
        choice = int(input("Enter your choice: "))
        if choice == 1:
            order_id = int(input("Enter order ID: "))
            timestamp = int(input("Enter timestamp: "))
            side = input("Enter side (buy/sell): ")
            quantity = int(input("Enter quantity: "))
            price = float(input("Enter price: "))
            add_order({"id": order_id, "timestamp": timestamp, "side": side, "quantity": quantity, "price": price})
        elif choice == 2:
            order_id = int(input("Enter order ID: "))
            new_quantity = int(input("Enter new quantity: "))
            modify_order_qty(order_id, new_quantity)
        elif choice == 3:
            order_id = int(input("Enter order ID: "))
            timestamp = int(input("Enter timestamp: "))
            side = input("Enter side (buy/sell): ")
            quantity = int(input("Enter quantity: "))
            price = float(input("Enter price: "))
            match_order({"id": order_id, "timestamp": timestamp, "side": side, "quantity": quantity, "price": price})
        elif choice == 4:
            display_order_book()
        elif choice == 5:
            break
        else:
            print("Invalid choice. Please try again.")