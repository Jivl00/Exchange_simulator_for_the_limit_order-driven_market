import json
import logging
import numpy as np
import pandas as pd
import tornado
from bokeh.server.server import Server
from bokeh.application import Application as BkApplication
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure
from bokeh.themes import built_in_themes
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource, DataTable, TableColumn, Button, TextInput,
    RadioButtonGroup, Div, Range1d
)
from src.client.client import Trader

logging.getLogger('bokeh').setLevel(logging.INFO)
config = json.load(open("../config/server_config.json"))
class WebTrader(Trader):
    def __init__(self, name, mode, config):
        super().__init__(name, mode, config)

    def receive_market_data(self, data):
        pass # Not needed for web client

# =====================
# Backend Variables
# =====================
balance = 1000  # Starting balance in dollars
volume = 10  # Starting trading volume

# =====================
# Bokeh App Initialization
# =====================
def main_page(doc):
    # doc.theme = built_in_themes['dark_minimal']

    # Reinitialize models to ensure they are unique per session
    local_balance = balance
    local_volume = volume
    trader = WebTrader("bokeh", "server", config)
    trader.register(1000)

    # Trader dynamic text
    trade_text = Div(text="<h2>Trader</h2>", width=300)


    balance_text = Div(text=f"<h3>Balance: ${local_balance:.2f}</h3>", width=300)
    volume_text = Div(text=f"<h3>Volume: {local_volume} lots</h3>", width=300)

    price_source = ColumnDataSource(data={'x': [], 'y': []})
    order_source = ColumnDataSource(data={'ID': [], 'price': [], 'quantity': [], 'side': []})
    hist_source = ColumnDataSource(data={'left': [], 'right': [], 'top': []})

    # =====================
    # Order Management UI
    # =====================
    price_input = TextInput(title="Price", value="100")
    quantity_input = TextInput(title="Quantity", value="1")
    side_selector = RadioButtonGroup(labels=["Buy", "Sell"], active=0)
    send_button = Button(label="Send Order", button_type="success")
    delete_button = Button(label="Delete Selected", button_type="danger")

    columns = [
        TableColumn(field="ID", title="ID"),
        TableColumn(field="price", title="Price"),
        TableColumn(field="quantity", title="Quantity"),
        TableColumn(field="side", title="Side"),
    ]
    order_table = DataTable(source=order_source, columns=columns, width=400, height=250)

    # =====================
    # Graphs
    # =====================
    price_fig = figure(title="Price Chart", width=600, height=300, sizing_mode="stretch_width")
    price_fig.line('x', 'y', source=price_source, line_width=2)

    hist_fig = figure(title="Order Book", width=600, height=300, sizing_mode="stretch_width")
    hist_fig.quad(top='top', bottom=0, left='left', right='right', source=hist_source, fill_color="blue",
                  line_color="black")


    # =====================
    # Callbacks
    # =====================
    def update_price():
        new_data = {'x': [len(price_source.data['x'])], 'y': [100 + np.random.randn()]}
        price_source.stream(new_data, rollover=50)

    def send_order():
        nonlocal local_balance, local_volume
        price = float(price_input.value)
        quantity = float(quantity_input.value)
        side = "Buy" if side_selector.active == 0 else "Sell"

        if side == "Buy" and local_balance < price * quantity:
            return

        if side == "Buy":
            local_balance -= price * quantity
            local_volume += quantity
        else:
            local_volume -= quantity
            local_balance += price * quantity

        balance_text.text = f"<h3>Balance: ${local_balance:.2f}</h3>"
        volume_text.text = f"<h3>Volume: {local_volume} lots</h3>"
        # order_book = trader.order_book_request("product1")
        order_book = "123"
        trade_text.text = f"<h2>Trader</h2><h3>Order Book: {order_book}</h3>"

        new_order = {'ID': [1], 'price': [price], 'quantity': [quantity], 'side': [side]}
        order_source.stream(new_order)
        update_histogram()
        trader.put_order({"side": "buy", "quantity": 1, "price": 9.0}, "product1")

    def delete_order():
        selected = order_source.selected.indices
        if selected:
            df = pd.DataFrame(order_source.data)
            df = df.drop(selected).reset_index(drop=True)
            order_source.data = df.to_dict(orient="list")
            update_histogram()

    def update_histogram():
        df = pd.DataFrame(order_source.data)
        if df.empty:
            hist_source.data = {'left': [], 'right': [], 'top': []}
            return
        bins = np.histogram(df['price'], bins=10)
        hist_source.data = {'left': bins[1][:-1], 'right': bins[1][1:], 'top': bins[0]}

    send_button.on_click(send_order)
    delete_button.on_click(delete_order)

    # Layouts
    controls = column(
        Div(text="<h2>Trading Panel</h2>"),
        balance_text, volume_text, trade_text,
        price_input, quantity_input, side_selector, send_button,
        Div(text="<h3>Order Book</h3>"),
        order_table, delete_button, width=400, sizing_mode="stretch_both"
    )

    graphs = column(price_fig, hist_fig, width=800, sizing_mode="stretch_both")
    layout = row(graphs, controls, sizing_mode="stretch_both")

    # Add to document
    doc.add_root(layout)
    doc.add_periodic_callback(update_price, 1000)



def make_app():
    tornado_app = tornado.web.Application([
        (r"/", main_page),
    ], debug=True, autoreload=True)

    # Configure Bokeh Server
    bokeh_app = BkApplication(FunctionHandler(main_page))
    viz_port = int(config["VIZ_PORT"])
    server = Server({'/': bokeh_app},
                    io_loop=tornado.ioloop.IOLoop.current(),
                    allow_websocket_origin=[f"localhost:{viz_port}",
                                            f"{config['HOST'].replace('http://', '')}:{viz_port}"],
                    port=viz_port)
    server.start()

    return tornado_app

if __name__ == "__main__":
    app = make_app()
    app.listen(config["PORT"])
    print(f"Website running on {config['HOST']}:{config['VIZ_PORT']}")
    tornado.ioloop.IOLoop.current().start()



