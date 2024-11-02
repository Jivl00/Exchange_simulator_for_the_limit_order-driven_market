import requests
import json
import pandas as pd
import simplefix

config = json.load(open("config/fix_config.json"))

BASE_URL = "http://127.0.0.1:8888"
BEGIN_STRING = config["BEGIN_STRING"]
TARGET = config["TARGET"]
SENDER = "49=fixer"
MSG_SEQ_NUM = 0


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


def fix_message_init():
    """
    Initialize a FIX message with standard header tags
    :return: simplefix.FixMessage object
    """
    global MSG_SEQ_NUM
    message = simplefix.FixMessage()
    message.append_string(BEGIN_STRING, header=True)
    message.append_string(TARGET, header=True)
    message.append_utc_timestamp(52, precision=6, header=True)
    message.append_pair(34, MSG_SEQ_NUM, header=True)  # MsgSeqNum
    MSG_SEQ_NUM += 1
    message.append_string(SENDER, header=True)  # SenderCompID
    return message

def order_stats(order_id):
    message = fix_message_init()
    message.append_pair(35, "H", header=True)  # MsgType = OrderStatusRequest
    message.append_pair(41, order_id)  # ClOrdID

    byte_buffer = message.encode()
    response = requests.post(f"{BASE_URL}/fix", json={"message": byte_buffer})
    response_data = response.json()
    print(response.json())
    # use eval to reconstruct the order object
    order = response_data['order']
    print(f"Order ID: {order['id']}")
    return order

def put_order(order):
    """
    Send a new order request to the FIX server
    :param order: Dictionary containing order details
    :return: None
    """
    message = fix_message_init()
    message.append_pair(35, "D", header=True)  # MsgType = NewOrderSingle
    message.append_pair(54, 1 if order['side'] == 'buy' else 2)  # Side
    message.append_pair(38, order['quantity'])  # Quantity
    message.append_pair(44, order['price'])  # Price

    byte_buffer = message.encode()
    response = requests.post(f"{BASE_URL}/fix", json={"message": byte_buffer})
    print(response.json())


def delete_order(ID):
    message = fix_message_init()
    message.append_pair(35, "F", header=True)  # MsgType = OrderCancelRequest
    message.append_pair(41, ID)  # OrigClOrdID

    byte_buffer = message.encode()
    response = requests.post(f"{BASE_URL}/fix", json={"message": byte_buffer})
    print(response.json())

def modify_order_qty(ID, quantity):
    message = fix_message_init()
    message.append_pair(35, "G", header=True)  # MsgType = OrderCancelReplaceRequest
    message.append_pair(41, ID)  # OrigClOrdID
    message.append_pair(38, quantity)  # Quantity

    byte_buffer = message.encode()
    response = requests.post(f"{BASE_URL}/fix", json={"message": byte_buffer})
    print(response.json())
def modify_order(ID, new_price=None, new_quantity=None):
    order = order_stats(ID)
    delete_order(ID)
    if new_price is not None:
        order['price'] = new_price
    if new_quantity is not None:
        order['quantity'] = new_quantity
    put_order(order)


if __name__ == "__main__":
    # Example usage
    put_order({"side": "buy", "quantity": 100, "price": 20.0, "user": "pepa"})
    put_order({"side": "sell", "quantity": 50, "price": 30.0, "user": "pepa"})
    put_order({"side": "buy", "quantity": 100, "price": 20.0, "user": "fixer"})
    display_order_book()
    order_stats(0)
    delete_order(2)
    modify_order_qty(0, 50)
    display_order_book()
    modify_order(1, new_price=25.0)
    display_order_book()
    put_order({"side": "sell", "quantity": 100, "price": 20.0, "user": "pepa"})
    display_order_book()
    # modify_order_qty(0, 50)
    # display_order_book()
    # put_order({"side": "buy", "quantity": 60, "price": 30.0, "user": "pepa"})
    # display_order_book()

    while False:
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
            put_order({"side": side, "quantity": quantity, "price": price,
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
