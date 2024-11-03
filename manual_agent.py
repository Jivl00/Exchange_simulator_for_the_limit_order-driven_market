from client import Initiator
import json

config = json.load(open("config/fix_config.json"))
manual_agent = Initiator("manual_agent", "server", config)

manual_agent.put_order({"side": "buy", "quantity": 100, "price": 20.0})
manual_agent.put_order({"side": "sell", "quantity": 50, "price": 30.0})
manual_agent.put_order({"side": "buy", "quantity": 100, "price": 20.0})
manual_agent.display_order_book(manual_agent.order_book_request())
print(manual_agent.order_stats(0))
manual_agent.delete_order(2)
manual_agent.modify_order_qty(0, 50)
manual_agent.display_order_book(manual_agent.order_book_request())
manual_agent.modify_order(1, new_price=25.0)
manual_agent.display_order_book(manual_agent.order_book_request())
manual_agent.put_order({"side": "sell", "quantity": 90, "price": 20.0})
manual_agent.display_order_book(manual_agent.order_book_request())
manual_agent.list_user_orders()


# manual_agent.put_order({"side": "sell", "quantity": 20, "price": 22.0})
# manual_agent.put_order({"side": "sell", "quantity": 10, "price": 22.0})
# manual_agent.put_order({"side": "buy", "quantity": 10, "price": 12.0})
# manual_agent.put_order({"side": "buy", "quantity": 15, "price": 11.0})
# manual_agent.put_order({"side": "buy", "quantity": 20, "price": 13.0})
# manual_agent.display_order_book2()