import json
import logging
import numpy as np
import pandas as pd
import datetime
import tornado
from bokeh.server.server import Server
from bokeh.application import Application as BkApplication
from bokeh.application.handlers.function import FunctionHandler
from bokeh.models import DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.models import Legend
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource, DataTable, TableColumn, Button, TextInput,
    RadioButtonGroup, Div
)
from ui.web_trader import WebTrader

logging.getLogger('bokeh').setLevel(logging.INFO)
config = json.load(open("../config/server_config.json"))

# =====================
# Backend Variables
# =====================


# =====================
# Bokeh App Initialization
# =====================
def main_page(doc):
    # doc.theme = built_in_themes['dark_minimal']

    # Reinitialize models to ensure they are unique per session
    initial_balance = 1000
    trader = WebTrader("bokeh", "server", config)
    trader.register(initial_balance)

    local_balance = initial_balance
    local_volume = 0

    # Trader dynamic text
    balance_text = Div(text=f"<h3>Balance: ${local_balance:.2f}</h3>", width=300)
    volume_text = Div(text=f"<h3>Volume: {local_volume} lots</h3>", width=300)

    price_source = ColumnDataSource(data={'x': [], 'mid_price': [], 'bid_price': [], 'ask_price': []})
    order_source = ColumnDataSource(data={'ID': [], 'price': [], 'quantity': [], 'side': []})
    hist_source = ColumnDataSource(data={'left': [], 'right': [], 'bid_top': [], 'ask_top': []})

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
    price_fig = figure(title="Price Chart", width=600, height=300, sizing_mode="stretch_width", x_axis_type="datetime")
    mid_line = price_fig.line('x', 'mid_price', source=price_source, line_width=2, color='blue', alpha=0.5,
                              )
    bid_line = price_fig.line('x', 'bid_price', source=price_source, line_width=4, color='green', alpha=0.5,
                              )
    ask_line = price_fig.line('x', 'ask_price', source=price_source, line_width=4, color='red', alpha=0.5,
                              )

    price_fig.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S")
    legend = Legend(items=[
        ("Mid Price", [mid_line]),
        ("Bid Price", [bid_line]),
        ("Ask Price", [ask_line])
    ], location="center", orientation="horizontal")
    price_fig.add_layout(legend, 'above')

    hist_fig = figure(title="Order Book", width=600, height=300, sizing_mode="stretch_width")
    hist_fig.quad(top='bid_top', bottom=0, left='left', right='right',
              color='green', alpha=0.5, legend_label='Bids', source=hist_source)
    hist_fig.quad(top='ask_top', bottom=0, left='left', right='right',
              color='red', alpha=0.5, legend_label='Asks', source=hist_source)
    hist_fig.legend.location = "top_left"
    hist_fig.legend.title = "Order Book"
    hist_fig.legend.items = [
        ("Bids", [hist_fig.renderers[-2]]),  # Bids are the second to last plot
        ("Asks", [hist_fig.renderers[-1]])   # Asks are the last plot
    ]


    # =====================
    # Callbacks
    # =====================
    def update():
        order_book = trader.order_book_request("product1")
        update_histogram(order_book)
        update_price(order_book)
        user_data = trader.user_balance("product1", verbose=False)
        local_balance = user_data["post_buy_budget"]
        local_volume = user_data["current_balance"]["post_sell_volume"]

        balance_text.text = f"<h3>Balance: ${local_balance:.2f}</h3>"
        volume_text.text = f"<h3>Volume: {local_volume} lots</h3>"

        user_orders = trader.list_user_orders("product1")
        new_orders = {'ID': [], 'price': [], 'quantity': [], 'side': []}

        # Iterate over the original orders
        if user_orders:
            for order_key, order in user_orders.items():
                new_orders['ID'].append(int(order['id']))  # Convert 'id' to an integer (if needed)
                new_orders['price'].append(order['price'])
                new_orders['quantity'].append(order['quantity'])
                new_orders['side'].append(order['side'])

            # Update the data source with the new orders
            order_source.data = new_orders
        else:
            order_source.data = {'ID': [None], 'price': [None], 'quantity': [None], 'side': [None]}


    def update_price(order_book):
        bids = order_book["Bids"]
        asks = order_book["Asks"]
        # datetime.datetime.min + datetime.timedelta(seconds=t // 1e9)
        time = order_book["Timestamp"]/1e9 # Convert nanoseconds to seconds
        time = datetime.datetime.fromtimestamp(time)
        if bids and asks:
            # mid_price = (bids[0]["Price"] + asks[0]["Price"]) / 2
            mid_price = np.nan
            bid_price = bids[0]["Price"] if bids else np.nan
            ask_price = asks[0]["Price"] if asks else np.nan
            # print(f"Mid price: {mid_price}")
            # print(f"Time: {time}")

            new_data = {
                'x': [time],
                'mid_price': [mid_price],
                'bid_price': [bid_price],
                'ask_price': [ask_price],
            }
            price_source.stream(new_data, rollover=50)

    def send_order():
        local_balance= 1000 #TODO:
        local_volume=10 # TODO
        price = int(price_input.value)
        quantity = int(quantity_input.value)
        side = "buy" if side_selector.active == 0 else "sell"

        if side == "buy" and local_balance < price * quantity:
            return

        if side == "buy":
            local_balance -= price * quantity
            local_volume += quantity
        else:
            local_volume -= quantity
            local_balance += price * quantity

        # balance_text.text = f"<h3>Balance: ${local_balance:.2f}</h3>"
        # volume_text.text = f"<h3>Volume: {local_volume} lots</h3>"
        # order_book = trader.order_book_request("product1")

        # new_order = {'ID': [1], 'price': [price], 'quantity': [quantity], 'side': [side]}
        # order_source.stream(new_order)
        trader.put_order({"side": side, "quantity": quantity, "price": price}, "product1")
        update()

    def delete_order():
        selected = order_source.selected.indices
        if not selected or not order_source.data['ID']:
            return
        order_id = order_source.data['ID'][selected[0]]
        if order_id:
            trader.delete_order(order_id, "product1")
            update()

    def update_histogram(order_book):

        # Extract Bids and Asks dataframes
        bids_df = pd.DataFrame(order_book.get('Bids', []))
        asks_df = pd.DataFrame(order_book.get('Asks', []))

        # Combine both Bids and Asks into a single dataframe
        # If Bids or Asks are empty, we only use the non-empty dataframe
        if not bids_df.empty and not asks_df.empty:
            df = pd.concat([bids_df[['Price', 'Quantity']], asks_df[['Price', 'Quantity']]], ignore_index=True)
        elif not bids_df.empty:
            df = bids_df[['Price', 'Quantity']]
        elif not asks_df.empty:
            df = asks_df[['Price', 'Quantity']]
        else:
            df = pd.DataFrame()  # Empty DataFrame if both are empty

        if df.empty:
            hist_source.data = {'left': [], 'right': [], 'bid_top': [], 'ask_top': []}
            return

        # Calculate histogram with 10 bins
        bins = np.histogram(df['Price'], bins=1000, range=(df['Price'].min(), df['Price'].max()))

        # Create an array of bin edges
        bin_edges = bins[1]

        # Create an array to store the cumulative quantity for each bin
        bid_bin_heights = np.zeros(len(bin_edges) - 1)
        ask_bin_heights = np.zeros(len(bin_edges) - 1)

        # Accumulate the quantity for each price in the appropriate bin (bids in green, asks in red)
        for i, row in df.iterrows():
            price = row['Price']
            quantity = row['Quantity']

            # Find the bin index for the current price
            bin_index = np.digitize(price, bin_edges) - 1
            if 0 <= bin_index < len(bid_bin_heights):
                if 'Price' in bids_df.columns and price in bids_df['Price'].values:
                    bid_bin_heights[bin_index] += quantity  # Bids are added to bid_bin_heights
                elif 'Price' in asks_df.columns and price in asks_df['Price'].values:
                    ask_bin_heights[bin_index] += quantity  # Asks are added to ask_bin_heights

        # Set the histogram data for the plot
        hist_source.data = {
            'left': bin_edges[:-1],  # Left edge of each bin
            'right': bin_edges[1:],  # Right edge of each bin
            'bid_top': bid_bin_heights,  # Cumulative bid quantity for each bin
            'ask_top': ask_bin_heights,  # Cumulative ask quantity for each bin
        }

    send_button.on_click(send_order)
    delete_button.on_click(delete_order)

    # Layouts
    controls = column(
        Div(text="<h2>Trading Panel</h2>"),
        balance_text, volume_text,
        price_input, quantity_input, side_selector, send_button,
        Div(text="<h3>Active orders</h3>"),
        order_table, delete_button, width=400, sizing_mode="stretch_both"
    )

    graphs = column(price_fig, hist_fig, width=800, sizing_mode="stretch_both")
    layout = row(graphs, controls, sizing_mode="stretch_both")

    # Add to document
    doc.add_root(layout)
    doc.add_periodic_callback(update, 1000)



def make_app():
    tornado_app = tornado.web.Application([
        (r"/", main_page),
    ], debug=True, autoreload=True)

    # Configure Bokeh Server
    bokeh_app = BkApplication(FunctionHandler(main_page))
    viz_port = int(config["VIZ_PORT"])
    server = Server({'/': bokeh_app},
                    io_loop=tornado.ioloop.IOLoop.current(),
                    allow_websocket_origin=[f"{config['HOST'].replace('http://', '')}:{viz_port}"],
                    port=viz_port)
    server.start()

    return tornado_app

if __name__ == "__main__":
    app = make_app()
    app.listen(0)
    print(f"Website running on {config['HOST']}:{config['VIZ_PORT']}")
    tornado.ioloop.IOLoop.current().start()



