import json
import logging
import numpy as np
import pandas as pd
import datetime
import tornado
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from bokeh.server.server import Server
from bokeh.application import Application as BkApplication
from bokeh.application.handlers.function import FunctionHandler
from bokeh.models import DatetimeTickFormatter
from bokeh.plotting import figure
from bokeh.models import Legend
from bokeh.layouts import column, row
from bokeh.models import (
    ColumnDataSource, DataTable, TableColumn, Button, TextInput,
    RadioButtonGroup, Div, HoverTool
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

    # Top screen info
    product_info = Div(text="<h1>Product: product1</h1>", width=300)

    # Bottom table info
    change_today_text = Div(text="<h3>Change Today: 0.0%</h3>", width=300)
    imbalance_index_text = Div(text="<h3>Imbalance Index: 0.0</h3>", width=300)
    minimum_order_size_text = Div(text="<h3>Order Size Granularity: 1</h3>", width=300)
    minimium_order_price_text = Div(text="<h3>Order Price Granularity: 0.01</h3>", width=300)
    trading_fee_text = Div(text="<h3>Trading Fee: 0.1%</h3>", width=300)

    # Trader dynamic text
    balance_text = Div(text=f"<h3>Balance: ${initial_balance:.2f}</h3>", width=300)
    volume_text = Div(text=f"<h3>Volume: {0} lots</h3>", width=300)

    price_source = ColumnDataSource(data={'x': [], 'bid_price': [], 'ask_price': []})
    order_source = ColumnDataSource(data={'ID': [], 'price': [], 'quantity': [], 'side': []})
    hist_source = ColumnDataSource(data={'left': [], 'right': [], 'bid_top': [], 'ask_top': []})
    hist_bid_table_source = ColumnDataSource(data={'bid_price': [], 'bid_volume': [], 'int_bid_price': []})
    hist_ask_table_source = ColumnDataSource(data={'ask_price': [], 'ask_volume': [], 'int_ask_price': []})

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
    price_fig = figure(
        width=600,
        frame_height=350,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        toolbar_location="right",
    )
    price_fig.toolbar.logo = None

    bid_line = price_fig.line('x', 'bid_price', source=price_source, line_width=4, color='green', alpha=0.5)
    ask_line = price_fig.line('x', 'ask_price', source=price_source, line_width=4, color='red', alpha=0.5)
    # Format the x-axis to show time in HH:MM:SS format
    price_fig.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S")
    legend = Legend(items=[
        ("Best Bid Price", [bid_line]),
        ("Best Ask Price", [ask_line])
    ], location="left", orientation="horizontal")
    price_fig.add_layout(legend, 'above')
    # Add separate hover tools for each line
    bid_hover = HoverTool(renderers=[bid_line], tooltips=[
        ("Time", "@x{%F %T}"),
        ("Bid Price", "@bid_price")
    ], formatters={'@x': 'datetime'}, mode='mouse')

    ask_hover = HoverTool(renderers=[ask_line], tooltips=[
        ("Time", "@x{%F %T}"),
        ("Ask Price", "@ask_price")
    ], formatters={'@x': 'datetime'}, mode='mouse')

    price_fig.add_tools(bid_hover, ask_hover)

    hist_fig = figure(title="Order Book", width=600, height=300, sizing_mode="stretch_width", toolbar_location="right")
    hist_fig.toolbar.logo = None
    hist_fig.quad(top='bid_top', bottom=0, left='left', right='right',
                  color='green', alpha=0.5, legend_label='Bids', source=hist_source)
    hist_fig.quad(top='ask_top', bottom=0, left='left', right='right',
                  color='red', alpha=0.5, legend_label='Asks', source=hist_source)
    hist_fig.legend.location = "top_left"
    hist_fig.legend.title = "Order Book"
    hist_fig.legend.items = [
        ("Bids", [hist_fig.renderers[-2]]),  # Bids are the second to last plot
        ("Asks", [hist_fig.renderers[-1]])  # Asks are the last plot
    ]

    data = {
        'price': [95.57, 95.49, 95.48, 95.41, 94.82],
        'volume': [40, 37, 61, 45, 75],
    }
    # Create a pandas DataFrame
    df = pd.DataFrame(data)

    # Create ColumnDataSource
    source = ColumnDataSource(df)
    source.data = data



    # Create the figure
    p = figure(title="Active orders", x_axis_label='Volume', y_axis_label='Price',
               height=400, width=800, toolbar_location=None, sizing_mode="stretch_width")
    p.axis.visible = False
    p.grid.visible = False
    p.toolbar.logo = None

    # Add horizontal bars (hbars) to represent volume at each price level
    p.hbar(y='int_bid_price', right='bid_volume', height=0.8, source=hist_bid_table_source, color="skyblue", alpha=0.6)
    # p.hbar(y='price', right='volume', height=0.8, source=source, color="skyblue", alpha=0.6)

    # text1 = p.text(x=10, y='int_bid_price',
    #        text='bid_price', text_font_size="10pt", text_align="left",
    #        text_baseline="middle", color="black", source=hist_bid_table_source)
    #
    # text2 = p.text(x=50, y='int_bid_price',
    #        text='bid_volume', text_font_size="10pt", text_align="left",
    #        text_baseline="middle", color="black", source=hist_bid_table_source)

    # p.text(x=200, y=source.data['price'],
    #        text=source.data['volume'].astype(str), text_font_size="10pt", text_align="right",
    #        text_baseline="middle", color="black")

    # p.text(x=10, y=max(df['price']) + 1, text=["Price"], text_font_size="10pt", text_align="center",
    #        text_baseline="bottom", color="black")
    #
    # p.text(x=200, y=max(df['price']) + 1, text=["Volume"], text_font_size="10pt",
    #        text_align="center", text_baseline="bottom", color="black")

    # =====================
    # Callbacks
    # =====================
    def update():
        order_book = trader.order_book_request("product1")
        update_histogram(order_book)
        update_histogram_table(order_book)
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

    def imbalance_index(asks, bids, alpha=0.5, level=3):
        """
        Calculate imbalance index for a given orderbook.
        :param asks: list of ask sizes (volumes)
        :param bids: list of bid sizes (volumes)
        :param alpha: parameter for imbalance index
        :param level: number of levels to consider
        :return: imbalance index
        """
        bids = bids[:level]
        asks = asks[:level]
        exp_factors = np.exp(-alpha * np.arange(level))

        # Calculate imbalance index
        V_bt = sum(bids * exp_factors[:len(bids)])
        V_at = sum(asks * exp_factors[:len(asks)])
        return (V_bt - V_at) / (V_bt + V_at)

    def update_price(order_book):
        bids = order_book["Bids"]
        asks = order_book["Asks"]
        # datetime.datetime.min + datetime.timedelta(seconds=t // 1e9)
        time = order_book["Timestamp"] / 1e9  # Convert nanoseconds to seconds
        time = datetime.datetime.fromtimestamp(time)
        bid_price = bids[0]["Price"] if bids else np.nan
        ask_price = asks[0]["Price"] if asks else np.nan
        imbalance = np.nan
        if bids and asks:
            bids_df = pd.DataFrame(bids)
            asks_df = pd.DataFrame(asks)
            bids_df = bids_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            asks_df = asks_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            imbalance = imbalance_index(asks_df['Quantity'].values, bids_df['Quantity'].values)

            new_data = {
                'x': [time],
                'bid_price': [bid_price],
                'ask_price': [ask_price],
            }
            price_source.stream(new_data, rollover=50)

    def send_order():
        price = float(price_input.value)
        quantity = int(quantity_input.value)
        side = "buy" if side_selector.active == 0 else "sell"

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
            bin_index = min(np.digitize(price, bin_edges) - 1, len(bid_bin_heights) - 1)
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

    def update_histogram_table(order_book):
        bids_df = pd.DataFrame(order_book.get('Bids', []))
        asks_df = pd.DataFrame(order_book.get('Asks', []))

        if not bids_df.empty:
            bids_df = bids_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
        if not asks_df.empty:
            asks_df = asks_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
        # Trim to top 10 bids and asks
        bids_df = bids_df.sort_values('Price', ascending=False).head(10)
        asks_df = asks_df.sort_values('Price', ascending=True).head(10)

        hist_bid_table_source.data = {
            'bid_price':  np.array(bids_df['Price']).astype(str),
            'bid_volume': bids_df['Quantity'],
            'int_bid_price': [i for i in range(1, len(bids_df) + 1)]
        }
        hist_ask_table_source.data = {
            'ask_price': asks_df['Price'],
            'ask_volume': asks_df['Quantity'],
            'int_ask_price': [i for i in range(1, len(asks_df) + 1)]
        }

        nonlocal p
        # text1.x =int(max(bids_df['Quantity']) * 0.1) if not bids_df.empty else 0
        # text2.x = int(max(bids_df['Quantity']) * 0.5) if not bids_df.empty else 0
        x_max = max(bids_df['Quantity']) if not bids_df.empty else 0
        p.text(x=int(x_max * 0.1), y='int_bid_price',
                       text='bid_price', text_font_size="10pt", text_align="left",
                       text_baseline="middle", color="black", source=hist_bid_table_source)

        p.text(x=int(x_max * 0.5), y='int_bid_price',
                       text='bid_volume', text_font_size="10pt", text_align="left",
                       text_baseline="middle", color="black", source=hist_bid_table_source)

    send_button.on_click(send_order)
    delete_button.on_click(delete_order)

    # Layouts
    info_top_row = row(product_info, sizing_mode="stretch_width")
    controls = column(
        Div(text="<h2>Trading Panel</h2>"),
        balance_text, volume_text,
        price_input, quantity_input, side_selector, send_button,
        Div(text="<h3>Active orders</h3>"),
        order_table, delete_button, width=400, sizing_mode="stretch_both"
    )
    info_table = column(change_today_text, imbalance_index_text, minimum_order_size_text, minimium_order_price_text,
                        trading_fee_text, width=400, sizing_mode="stretch_width")

    table = column(info_top_row, p, info_table, width=400, sizing_mode="fixed")
    graphs = column(price_fig, hist_fig, width=750, sizing_mode="fixed")
    layout = row(table, graphs, controls, sizing_mode="stretch_both")

    # Add to document
    doc.add_root(layout)
    doc.add_periodic_callback(update, 1000)


def make_app():
    """
    Create a Tornado web application with a Bokeh server application.
    :return: Tornado web application
    """
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
