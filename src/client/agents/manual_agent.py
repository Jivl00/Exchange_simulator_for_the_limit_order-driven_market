from src.client.algorithmic_trader import AlgorithmicTrader
import json

product1 = "product1"
config = json.load(open("../config/server_config.json"))
manual_agent = AlgorithmicTrader("manual_agent", "server", config)
manual_agent.login_via_UUID("6df84c34-b098-4dd5-8fd7-8cfcbeeb7e15")
manual_agent.display_order_book(manual_agent.order_book_request(product1), product=product1, aggregated=False)

