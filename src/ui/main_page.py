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
    RadioButtonGroup, Div, HoverTool, LegendItem, GroupBox, CustomJS
)
from ui.web_trader import WebTrader

logging.getLogger('bokeh').setLevel(logging.INFO)
config = json.load(open("../config/server_config.json"))


# =====================
# Backend Variables
# =====================
common_style = "font-family: 'Arial', sans-serif; font-size: 12px;"
label_style = f"{common_style} color: rgba(0, 0, 0, 0.5);"
value_style = f"{common_style} color: rgba(0, 0, 0, 1);"

# =====================
# Bokeh App Initialization
# =====================
def main_page(doc):
    # Reinitialize models to ensure they are unique per session
    initial_balance = 10000
    trader = WebTrader("bokeh", "server", config)
    user_id = trader.register(initial_balance)

    # Top screen info
    product_info = Div(text="<h1 style='opacity: 0.5;'>StackUnderflow Stocks</h1>", width=300)
    info_table = column(
        Div(text=f""),
        sizing_mode="stretch_both"
    )

    # Trader dynamic text
    balance_text = Div(text=f"", width=300)
    quantity_text = Div(text=f"", width=300)
    fee_text = Div(text=f"", width=300)
    popup = Div(text=f"", width=300)

    price_source = ColumnDataSource(data={'x': [], 'bid_price': [], 'ask_price': []})
    order_source = ColumnDataSource(data={'ID': [], 'price': [], 'quantity': [], 'side': []})
    history_source = ColumnDataSource(data={'time': [], 'price': [], 'quantity': [], 'side': []})
    hist_source = ColumnDataSource(data={'left': [], 'right': [], 'bid_top': [], 'ask_top': []})
    mid_price_source = ColumnDataSource(data={'x': [], 'y': []})
    hist_bid_table_source = ColumnDataSource(
        data={'bid_price': [], 'bid_quantity': [], 'int_bid_price': [], 'price_label': [],
              'price_pos': [], 'quantity_label': [], 'quantity_pos': []})
    hist_ask_table_source = ColumnDataSource(
        data={'ask_price': [], 'ask_quantity': [], 'int_ask_price': [], 'price_pos': [], 'quantity_pos': []})

    # =====================
    # Order Management UI
    # =====================
    user_id_input = TextInput(title="User ID", value=user_id, width=300)
    login_button = Button(label="Login", button_type="success", width=300)
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
    order_table = DataTable(source=order_source, columns=columns, width=365, height=250)
    # replace id colum with timestamp
    columns[0] = TableColumn(field="time", title="Timestamp")
    history_table = DataTable(source=history_source, columns=columns, height=200, sizing_mode="stretch_width")
    history_table_group = GroupBox(
        child=history_table,
        title="Order History",
        sizing_mode="stretch_width",
    )

    # =====================
    # Graphs
    # =====================
    # Price chart
    # --------------------------------
    price_fig = figure(
        width=600,
        frame_height=250,
        sizing_mode="stretch_width",
        x_axis_type="datetime",
        toolbar_location="right",
        tools="pan,box_zoom,wheel_zoom,reset",
        outline_line_color=None
    )
    price_fig.toolbar.logo = None
    price_fig.background_fill_color = "#f9f9f9"

    bid_line = price_fig.line('x', 'bid_price', source=price_source, line_width=4, color='green', alpha=0.5)
    ask_line = price_fig.line('x', 'ask_price', source=price_source, line_width=4, color='red', alpha=0.5)
    # Format the x-axis to show time in HH:MM:SS format
    price_fig.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S")
    legend = Legend(items=[
        ("Best Bid Price", [bid_line]),
        ("Best Ask Price", [ask_line])
    ], location="left", orientation="horizontal", click_policy="hide", spacing=20)
    price_fig.add_layout(legend, 'above')
    # Add separate hover tools for each line
    bid_hover = HoverTool(renderers=[bid_line], tooltips=[
        ("Time", "@x{%F %T}"),
        ("Bid Price", "@bid_price{0.00}")
    ], formatters={'@x': 'datetime'}, mode='mouse', visible=False)

    ask_hover = HoverTool(renderers=[ask_line], tooltips=[
        ("Time", "@x{%F %T}"),
        ("Ask Price", "@ask_price{0.00}")
    ], formatters={'@x': 'datetime'}, mode='mouse', visible=False)

    price_fig.add_tools(bid_hover, ask_hover)

    price_fig_group = GroupBox(
        child=price_fig,
        title="Price Chart",
        sizing_mode="stretch_width",
    )

    # Order Book chart
    # --------------------------------
    hist_fig = figure(
        width=600,
        height=300,
        sizing_mode="stretch_width",
        toolbar_location="right",
        tools="pan,box_zoom,wheel_zoom,reset",
    )
    hist_fig.toolbar.logo = None
    bid_renderer = hist_fig.quad(top='bid_top', bottom=0, left='left', right='right',
                                 color='green', alpha=0.5, source=hist_source)
    ask_renderer = hist_fig.quad(top='ask_top', bottom=0, left='left', right='right',
                                 color='red', alpha=0.5, source=hist_source)
    mid_price_line = hist_fig.line('x', 'y', source=mid_price_source, line_width=2, color='blue', alpha=0.5,
                                   line_dash='dashed')
    legend = Legend(items=[
        LegendItem(label="Bids", renderers=[hist_fig.renderers[0]]),
        LegendItem(label="Asks", renderers=[hist_fig.renderers[1]]),
        LegendItem(label="Mid Price", renderers=[mid_price_line])
    ], location="top_left", orientation="horizontal", click_policy="hide", spacing=20)
    hist_fig.add_layout(legend, 'above')
    hist_fig.xaxis.axis_label = "Price"
    hist_fig.yaxis.axis_label = "Quantity"
    # Add hover tool to show price and quantity
    bid_hover = HoverTool(renderers=[bid_renderer], tooltips=[
        ("Price", "@left{0.00}"),
        ("Quantity", "@bid_top")
    ], mode='mouse', visible=False)
    ask_hover = HoverTool(renderers=[ask_renderer], tooltips=[
        ("Price", "@left{0.00}"),
        ("Quantity", "@ask_top")
    ], mode='mouse', visible=False)
    mid_price_hover = HoverTool(renderers=[mid_price_line], tooltips=[
        ("Mid Price", "@x{0.00}")
    ], mode='mouse', visible=False)
    hist_fig.add_tools(bid_hover, ask_hover, mid_price_hover)

    hist_fig_group = GroupBox(
        child=hist_fig,
        title="Order Book",
        sizing_mode="stretch_width",
    )

    # Order Book table
    # --------------------------------
    bid_book_fig = figure(height=250, width=300, toolbar_location=None, tools="")
    bid_book_fig.axis.visible = False
    bid_book_fig.grid.visible = False
    bid_book_fig.toolbar.logo = None

    ask_book_fig = figure(height=230, width=300, toolbar_location=None, tools="")
    ask_book_fig.axis.visible = False
    ask_book_fig.grid.visible = False
    ask_book_fig.toolbar.logo = None

    bid_book_fig.hbar(y='int_bid_price', right='bid_quantity', height=0.8, source=hist_bid_table_source,
    color = "forestgreen", alpha = 0.3)
    ask_book_fig.hbar(y='int_ask_price', right='ask_quantity', height=0.8, source=hist_ask_table_source, color="salmon",
    alpha = 0.3)
    # Add price column to the left of the bid quantity
    bid_book_fig.text(x='price_pos', y='int_bid_price',
    text = 'bid_price', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "forestgreen", source = hist_bid_table_source)
    bid_book_fig.text(x='price_pos', y='int_bid_price',
    text = 'price_label', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "black", source = hist_bid_table_source)
    # Add quantity column to the right of the bid quantity
    bid_book_fig.text(x='quantity_pos', y='int_bid_price',
    text = 'bid_quantity', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "forestgreen", source = hist_bid_table_source)
    bid_book_fig.text(x='quantity_pos', y='int_bid_price',
    text = 'quantity_label', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "black", source = hist_bid_table_source)
    # Add price column to the left of the ask quantity
    ask_book_fig.text(x='price_pos', y='int_ask_price',
    text = 'ask_price', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "red", source = hist_ask_table_source)
    # Add quantity column to the right of the ask quantity
    ask_book_fig.text(x='quantity_pos', y='int_ask_price',
    text = 'ask_quantity', text_font_size = "10pt", text_align = "left",
    text_baseline = "middle", color = "red", source = hist_ask_table_source)

    table_book_group = GroupBox(
        child=column(bid_book_fig, ask_book_fig),
        title="Active orders",
        width=320,
        height=480,
        sizing_mode="fixed",
    )

    # =====================
    # Callbacks
    # =====================
    def update():
        order_book = trader.order_book_request("product1")
        update_histogram(order_book)
        update_histogram_table(order_book)
        mid_price, imbalance = update_price(order_book)
        user_data = trader.user_balance("product1", verbose=False)
        local_balance = user_data["post_buy_budget"]
        local_quantity = user_data["current_balance"]["post_sell_volume"]

        balance_text.text = f"""
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span style="{label_style}">Remaining Balance:</span>
                                <span style="{value_style}">${local_balance:.2f}</span>
                            </div>
        
                            """
        quantity_text.text = f"""
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span style="{label_style}">Owned Quantity:</span>
                                <span style="{value_style}">{local_quantity}</span>
                            </div>
                            """
        fee_text.text = f"""
            <div style="display: flex; flex-direction: column; gap: 3px; padding: 5px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="{label_style}; font-weight: bold;">Trading Fee:</span>
                    <span style="{value_style}; color: #d9534f; font-weight: bold;">0.01</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="{label_style};">+ Percentage of Price:</span>
                    <span style="{value_style}; color: #d9534f;">0.1%</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="{label_style};">+ Percentage of quantity:</span>
                    <span style="{value_style}; color: #d9534f;">0.5%</span>
                </div>
            </div>
        """

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

        start_of_day_price = 100
        change_today = round(((mid_price - start_of_day_price) / start_of_day_price) * 100, 2)
        change_today_color = "green" if change_today >= 0 else "red"
        change_today = f'<span style="color: {change_today_color};">{change_today}%</span>'

        data = {
            "Change Today": change_today,
            "Imbalance Index": str(round(imbalance, 2)),
            "Order Size Granularity": "1",
            "Order Price Granularity": "0.01",
        }

        # Updated info_table with title and dynamic values
        nonlocal info_table
        info_table.children[0].text = f"""
            <div style="border: 1.6px solid rgba(0, 0, 0, 0.1); padding: 10px; width: 290px;">
                {''.join(f'<div style="display: flex; justify-content: space-between; margin-bottom: 5px;">'
                         f'<span style="{label_style}">{key}:</span>'
                         f'<span style="{value_style}">{value}</span>'
                         '</div>' for key, value in data.items())}
            </div>
        """

    def calculate_imbalance_index(asks, bids, alpha=0.5, level=3):
        """
        Calculate imbalance index for a given orderbook.
        :param asks: list of ask sizes (quantitys)
        :param bids: list of bid sizes (quantitys)
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
        mid_price = np.nan
        imbalance = np.nan
        if bids and asks:
            bids_df = pd.DataFrame(bids)
            asks_df = pd.DataFrame(asks)
            bids_df = bids_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            asks_df = asks_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            imbalance = calculate_imbalance_index(asks_df['Quantity'].values, bids_df['Quantity'].values)
            mid_price = (bids[0]["Price"] + asks[0]["Price"]) / 2
            mid_price_source.data['x'] = [mid_price, mid_price]

            new_data = {
                'x': [time],
                'bid_price': [bid_price],
                'ask_price': [ask_price],
            }
            price_source.stream(new_data, rollover=50)
        return mid_price, imbalance

    def hide_popup():
        popup.styles = {"display": "none"}

    def send_order():
        price = float(price_input.value)
        quantity = int(quantity_input.value)
        side = "buy" if side_selector.active == 0 else "sell"

        _, status = trader.put_order({"side": side, "quantity": quantity, "price": price}, "product1")
        if status is False:
            alert_message = "Order put failed. Please check the order details and remaining balance."
            popup.text = f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="{label_style}">Status:</span>
                    <span style="{value_style}; color: red;">{alert_message}</span>
                </div>
            """
        else:
            alert_message = ""
            if status is True:
                alert_message = "Order successfully added to the order book."
            elif status is None:
                alert_message = "Order fulfilled successfully."

            popup.text = f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="{label_style}">Status:</span>
                    <span style="{value_style}; color: green;">{alert_message}</span>
                </div>
            """
            history_source.stream({
                'time': [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],  # Convert datetime to string
                'price': [price],
                'quantity': [quantity],
                'side': [side]
            })
            update()
        popup.styles = {"display": "block"}
        doc.add_timeout_callback(hide_popup, 3000)

    def delete_order():
        selected = order_source.selected.indices
        if not selected or not order_source.data['ID'] or selected[0] >= len(order_source.data['ID']):
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

        price_min = df['Price'].min()
        price_max = df['Price'].max()
        price_range = price_max - price_min
        granularity = 0.01
        num_bins = int(price_range / granularity)
        num_bins = max(num_bins, 10)
        bins = np.histogram(df['Price'], bins=num_bins, range=(price_min, price_max))

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
        mid_price_source.data['y'] = [0, max(bid_bin_heights.max(), ask_bin_heights.max())]
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
            bids_df = bids_df.sort_values('Price', ascending=False).head(10)  # Get top 10 bids
            hist_bid_table_source.data = {
                'bid_price': np.array(bids_df['Price']).astype(str).tolist() + [""],
                'bid_quantity': bids_df['Quantity'].to_numpy().tolist() + [""],
                'int_bid_price': [i for i in range(1, len(bids_df) + 2)],  # + 2 because of the extra row
                "price_label": [""] * (len(bids_df)) + ["Price"],
                "price_pos": [bids_df["Quantity"].max() * 0.1] * (len(bids_df) + 1),
                "quantity_label": [""] * (len(bids_df)) + ["Quantity"],
                "quantity_pos": [bids_df["Quantity"].max() * 0.5] * (len(bids_df) + 1)
            }
        else:
            hist_bid_table_source.data = {'bid_price': [], 'bid_quantity': [], 'int_bid_price': [], 'price_label': [],
                                          'price_pos': [], 'quantity_label': [], 'quantity_pos': []}

        if not asks_df.empty:
            asks_df = asks_df.groupby('Price', as_index=False).agg(
                {'Quantity': 'sum', 'ID': 'count', 'User': 'first'})
            asks_df = asks_df.sort_values('Price', ascending=True).head(10)  # Get top 10 asks
            asks_df = asks_df.iloc[::-1]
            hist_ask_table_source.data = {
                'ask_price': np.array(asks_df['Price']).astype(str),
                'ask_quantity': asks_df['Quantity'],
                'int_ask_price': [i for i in range(1, len(asks_df) + 1)],
                "price_pos": [asks_df["Quantity"].max() * 0.1] * len(asks_df),
                "quantity_pos": [asks_df["Quantity"].max() * 0.5] * len(asks_df)
            }
        else:
            hist_ask_table_source.data = {'ask_price': [], 'ask_quantity': [], 'int_ask_price': [], 'price_pos': [],
                                          'quantity_pos': []}

    login_button.on_click(lambda: trader.PROTOCOL.set_sender(user_id_input.value))
    send_button.on_click(send_order)
    delete_button.on_click(delete_order)

    # Layouts
    info_top_row = row(product_info, sizing_mode="stretch_width")
    user_id_group = GroupBox(
        child=column(user_id_input, login_button),
        title="Login",
        sizing_mode="stretch_width",
    )
    new_order_group = GroupBox(
        child=column(balance_text, quantity_text,fee_text, price_input, quantity_input, side_selector, send_button,
                     popup),
        title="New Order",
        sizing_mode="stretch_width",
    )
    user_orders_group = GroupBox(
        child=column(order_table, delete_button),
        title="Active User Orders",
    )
    controls = column(
        user_id_group,
        new_order_group,
        user_orders_group, width=400, sizing_mode="stretch_height",
    )
    control_box = GroupBox(
        child=controls,
        title="Trading Panel",
        sizing_mode="stretch_height",
    )
    info_table_group = GroupBox(
        child=info_table,
        title="Trading Details",
        sizing_mode="stretch_height",
        margin=(40, 0, 0, 0),
    )

    table = column(info_top_row, table_book_group, info_table_group, width=325, sizing_mode="stretch_height")
    graphs = column(price_fig_group, hist_fig_group, history_table_group, width=750, sizing_mode="fixed")
    layout = row(table, graphs, control_box, sizing_mode="stretch_both")


    doc.title = "StackUnderflow Stocks"
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
