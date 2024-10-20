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


def modify_order(order_id, new_price=None, new_quantity=None):
    data = {
        "order_id": order_id
    }
    if new_price:
        data["new_price"] = new_price
    if new_quantity:
        data["new_quantity"] = new_quantity
    response = requests.post(f"{BASE_URL}/modify_order", json=data)
    print(response.json())


def delete_order(order_id):
    data = {
        "order_id": order_id
    }
    response = requests.post(f"{BASE_URL}/delete_order", json=data)
    print(response.json())


def list_user_orders(user):
    response = requests.get(f"{BASE_URL}/list_user_orders?user={user}")
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
    add_order({"side": "buy", "quantity": 100, "price": 20.0, "user": "pepa"})
    add_order({"side": "sell", "quantity": 50, "price": 30.0, "user": "pepa"})
    display_order_book()
    modify_order_qty(0, 50)
    display_order_book()
    add_order({"side": "buy", "quantity": 60, "price": 30.0, "user": "pepa"})
    display_order_book()

    while True:
        print("1. Add order")
        print("2. Modify order quantity")
        print("3. Modify order")
        print("4. Delete order")
        print("5. List user orders")
        print("6. Display order book")
        print("7. Exit")
        choice = int(input("Enter your choice: "))
        if choice == 1:
            user = input("Enter user: ")
            side = input("Enter side (buy/sell): ")
            quantity = int(input("Enter quantity: "))
            price = float(input("Enter price: "))
            add_order({"side": side, "quantity": quantity, "price": price,
                       "user": user})
        elif choice == 2:
            order_id = int(input("Enter order ID: "))
            new_quantity = int(input("Enter new quantity: "))
            modify_order_qty(order_id, new_quantity)
        elif choice == 3:
            order_id = int(input("Enter order ID: "))
            new_price = float(input("Enter new price (or leave blank): ") or "nan")
            new_quantity = int(input("Enter new quantity (or leave blank): ") or "nan")
            modify_order(order_id, new_price if not pd.isna(new_price) else None,
                         new_quantity if not pd.isna(new_quantity) else None)
        elif choice == 4:
            order_id = int(input("Enter order ID: "))
            delete_order(order_id)
        elif choice == 5:
            user = input("Enter user: ")
            list_user_orders(user)
        elif choice == 6:
            display_order_book()
        elif choice == 7:
            break
        else:
            print("Invalid choice. Please try again.")
