from src.client.client import Client
import json

config = json.load(open("config/server_config.json"))
manual_agent = Client("manual_agent", "server", config)
manual_agent2 = Client("manual_agent2", "server", config)

product1 = "product1"
product2 = "product2"

manual_agent.put_order({"side": "buy", "quantity": 1, "price": 25.0}, product1)
manual_agent2.put_order({"side": "sell", "quantity": 2, "price": 20.0}, product1)
manual_agent.put_order({"side": "buy", "quantity": 3, "price": 21.0}, product1)
manual_agent2.put_order({"side": "buy", "quantity": 20, "price": 21.0}, product1)
manual_agent.display_order_book(manual_agent.order_book_request(product1), product=product1)
print()
manual_agent.list_user_orders(product1)
manual_agent2.list_user_orders(product1)
manual_agent.user_balance(product1)
h = manual_agent.historical_order_books(product1, 10)

# manual_agent.put_order({"side": "buy", "quantity": 100, "price": 20.0}, product1)
# manual_agent.put_order({"side": "sell", "quantity": 50, "price": 30.0}, product1)
# manual_agent.put_order({"side": "buy", "quantity": 100, "price": 20.0}, product2)
# manual_agent.display_order_book(manual_agent.order_book_request(product1), product1)
# print(manual_agent.order_stats(0, product1))
# manual_agent.delete_order(2, product1)
# manual_agent.modify_order_qty(0, 50, product1)
# manual_agent.display_order_book(manual_agent.order_book_request(product1), product1)
# manual_agent.modify_order(1, product1, new_price=25.0)
# manual_agent.display_order_book(manual_agent.order_book_request(product1), product1)
# manual_agent.put_order({"side": "sell", "quantity": 90, "price": 20.0}, product2)
# manual_agent.display_order_book(manual_agent.order_book_request(product2), product2)
# manual_agent.list_user_orders(product1)
# manual_agent.list_user_orders(product2)


# manual_agent.put_order({"side": "sell", "quantity": 20, "price": 22.0})
# manual_agent.put_order({"side": "sell", "quantity": 10, "price": 22.0})
# manual_agent.put_order({"side": "buy", "quantity": 10, "price": 12.0})
# manual_agent.put_order({"side": "buy", "quantity": 15, "price": 11.0})
# manual_agent.put_order({"side": "buy", "quantity": 20, "price": 13.0})
# manual_agent.display_order_book2()