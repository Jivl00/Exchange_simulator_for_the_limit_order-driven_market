import json

import simplefix
from src.protocols.IProtocol import IProtocol


class FIXProtocol(IProtocol):
    def __init__(self, sender, target="unknown"):
        super().__init__()
        self.version = "FIX.4.4"
        self.BEGIN_STRING = "8=" + self.version
        self.TARGET = "56=" + target
        self.SENDER = "49=" + sender
        self.MSG_SEQ_NUM = 0

        self.parser = simplefix.parser.FixParser()

    def set_target(self, target):
        self.TARGET = "56=" + target

    def fix_message_init(self):
        """
        Initialize a FIX message with standard header tags.
        :return: simplefix.FixMessage object
        """
        message = simplefix.FixMessage()
        message.append_string(self.BEGIN_STRING, header=True)
        message.append_string(self.TARGET, header=True)
        message.append_string(self.SENDER, header=True)
        message.append_utc_timestamp(52, precision=6, header=True)
        message.append_pair(34, self.MSG_SEQ_NUM, header=True)
        self.MSG_SEQ_NUM += 1
        return message

    def OrderStatusRequest_encode(self, data):
        ID = data["ID"]
        message = self.fix_message_init()
        message.append_pair(35, "H", header=True)  # MsgType = OrderStatusRequest
        message.append_pair(41, ID)  # ClOrdID
        return message

    def NewOrderSingle_encode(self, data):
        order = data["order"]
        message = self.fix_message_init()
        message.append_pair(35, "D", header=True)  # MsgType = NewOrderSingle
        message.append_pair(54, 1 if order['side'] == 'buy' else 2)  # Side
        message.append_pair(38, order['quantity'])  # Quantity
        message.append_pair(44, order['price'])  # Price
        return message

    def OrderCancelRequest_encode(self, data):
        ID = data["ID"]
        message = self.fix_message_init()
        message.append_pair(35, "F", header=True)  # MsgType = OrderCancelRequest
        message.append_pair(41, ID)  # ClOrdID
        return message

    def OrderModifyRequestQty_encode(self, data):
        ID = data["ID"]
        quantity = data["quantity"]
        message = self.fix_message_init()
        message.append_pair(35, "G", header=True)  # MsgType = OrderCancelReplaceRequest
        message.append_pair(41, ID)  # OrigClOrdID
        message.append_pair(38, quantity)  # Quantity
        return message

    def MarketDataRequest_encode(self, data):
        depth = data["depth"]
        message = self.fix_message_init()
        message.append_pair(35, "V", header=True)  # MsgType = MarketDataRequest
        message.append_pair(263, 0)  # SubscriptionRequestType = Snapshot
        message.append_pair(264, depth)  # MarketDepth
        return message

    def UserOrderStatusRequest_encode(self, data):
        message = self.fix_message_init()
        message.append_pair(35, "AF", header=True)  # MsgType = OrderMassStatusRequest
        message.append_pair(585, 8)  # MassStatusReqType = Status for orders for a PartyID
        message.append_pair(448, self.SENDER.split('=')[1])  # PartyID
        return message

    def OrderStatus_encode(self, data):
        order = data["order"]
        message = self.fix_message_init()
        message.append_pair(35, "8")  # ExecutionReport
        message.append_pair(150, "1")  # ExecType = Partially filled
        if order:
            order = order.__json__()
            message.append_pair(39, "1")  # OrdStatus = Remaining (partially filled) quantity
            message.append_pair(37, order['id'])  # OrderID
            message.append_pair(54, 1 if order['side'] == 'buy' else 2)  # Side
            message.append_pair(151, order['quantity'])  # LeavesQty
            message.append_pair(44, order['price'])  # Price
        else:
            message.append_pair(39, "8")  # OrdStatus = Rejected
        return message

    def ExecutionReport_encode(self, data):
        order_id = data["order_id"]
        status = data["status"]
        message = self.fix_message_init()
        message.append_pair(35, "8")
        message.append_pair(37, order_id)
        message.append_pair(150, "0")  # ExecType = New
        if status is True:  # Order partially matched
            message.append_pair(39, "1")
        elif status is None:  # Order fully matched
            message.append_pair(39, "2")
        else:  # Order match failed
            message.append_pair(39, "8")

        return message

    def ExecutionReportCancel_encode(self, data):
        message = self.fix_message_init()
        message.append_pair(37, data["order_id"])
        message.append_pair(39, "4")  # OrdStatus = Canceled
        status = data["status"]
        if status:
            message.append_pair(35, "8")  # ExecutionReport
            message.append_pair(150, "4")  # ExecType = Canceled
        else:
            message.append_pair(35, "9")  # OrderCancelReject

        return message

    def ExecutionReportCancelReplace_encode(self, data):
        message = self.fix_message_init()
        message.append_pair(37, data["order_id"])
        message.append_pair(39, "5")  # OrdStatus = Replaced
        status = data["status"]
        if status:
            message.append_pair(35, "8")
            message.append_pair(150, "5")  # ExecType = Replaced
        else:
            message.append_pair(35, "9")

        return message

    def MarketDataSnapshot_encode(self, data):
        order_book = data["order_book"]
        message = self.fix_message_init()
        message.append_pair(35, "W")
        message.append_pair(58, json.dumps(order_book))
        return message

    def UserOrders_encode(self, data):
        orders = data["user_orders"]
        message = self.fix_message_init()
        message.append_pair(35, "8")
        message.append_pair(150, 2) # Filled
        message.append_pair(58, json.dumps(orders))
        return message

    def encode(self, data):
        msg_types_map = {
            # Client -> Server
            "OrderStatusRequest": self.OrderStatusRequest_encode,
            "NewOrderSingle": self.NewOrderSingle_encode,
            "OrderCancelRequest": self.OrderCancelRequest_encode,
            "OrderModifyRequestQty": self.OrderModifyRequestQty_encode,
            "MarketDataRequest": self.MarketDataRequest_encode,
            "UserOrderStatusRequest": self.UserOrderStatusRequest_encode,

            # Server -> Client
            "OrderStatus": self.OrderStatus_encode,
            "ExecutionReport": self.ExecutionReport_encode,
            "ExecutionReportCancel": self.ExecutionReportCancel_encode,
            "ExecutionReportModify": self.ExecutionReportCancelReplace_encode,
            "MarketDataSnapshot": self.MarketDataSnapshot_encode,
            "UserOrderStatus": self.UserOrders_encode,

        }
        # TODO unknown message type error handling
        msg_type = data["msg_type"]
        message = msg_types_map[msg_type](data)
        byte_buffer = message.encode()
        return byte_buffer

    def parse_message(self, msg):
        """
        Parse the incoming FIX message.
        :param msg: FIX message
        :return: Decoded message
        """
        self.parser.append_buffer(msg)
        message = self.parser.get_message()
        return message

    def OrderStatus_decode(self, data):
        if data.get(39).decode() == '8':  # OrderStatus = Rejected
            return None
        order = {'id': data.get(37).decode(), 'side': 'buy' if data.get(54).decode() == '1' else 'sell',
                 'quantity': int(data.get(151).decode()), 'price': float(data.get(44).decode())}
        return order

    def ExecutionReport_decode(self, data):
        order_id = data.get(37).decode()
        status = data.get(39).decode()
        if status == '1':
            status = True
        elif status == '2':
            status = None
        else:
            status = False
        return {"order_id": order_id, "status": status}

    def MarketDataSnapshot_decode(self, data):
        order_book = json.loads(data.get(58).decode())
        order_book = json.loads(order_book)
        return {"order_book": order_book}

    def OrderStatusRequest_decode(self, data):
        order_id = data.get(41).decode()
        sender = data.get(49).decode()
        return {"id": order_id, "sender": sender}

    def UserOrders_decode(self, data):
        user_orders = json.loads(data.get(58).decode())
        return {"user_orders": user_orders}

    def NewOrderSingle_decode(self, data):

        order = {
            "user": data.get(49).decode(),
            "side": "buy" if data.get(54).decode() == '1' else 'sell',
            "quantity": int(data.get(38).decode()),
            "price": float(data.get(44).decode())
        }
        return {"order": order}

    def OrderCancelRequest_decode(self, data):
        order_id = data.get(41).decode()
        return {"order_id": order_id}

    def OrderModifyRequestQty_decode(self, data):
        order_id = data.get(41).decode()
        quantity = int(data.get(38).decode())
        return {"order_id": order_id, "quantity": quantity}

    def UserOrderStatusRequest_decode(self, data):
        user = data.get(49).decode()
        return {"user": user}

    def decode(self, message):
        msg_type = message['msg_type']
        message = self.parse_message(message['message'])
        msg_types_map = {
            # Client -> Server
            "OrderStatus": self.OrderStatus_decode,
            "ExecutionReport": self.ExecutionReport_decode,
            "MarketDataSnapshot": self.MarketDataSnapshot_decode,
            "UserOrderStatus": self.UserOrders_decode,

            # Server -> Client
            "OrderStatusRequest": self.OrderStatusRequest_decode,
            "NewOrderSingle": self.NewOrderSingle_decode,
            "OrderCancelRequest": self.OrderCancelRequest_decode,
            "OrderModifyRequestQty": self.OrderModifyRequestQty_decode,
            "UserOrderStatusRequest": self.UserOrderStatusRequest_decode,

        }
        data = msg_types_map[msg_type](message)
        return data
