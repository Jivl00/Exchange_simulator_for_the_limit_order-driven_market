import simplefix
from src.protocols.IProtocol import IProtocol


class FIXProtocol(IProtocol):
    def __init__(self, sender, target):
        super().__init__()
        self.version = "FIX.4.4"
        self.BEGIN_STRING = "8=" + self.version
        self.TARGET = "56=" + target
        self.SENDER = "49=" + sender
        self.MSG_SEQ_NUM = 0

        self.parser = simplefix.parser.FixParser()

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

    def OrderStatusRequest(self, data):
        ID = data["ID"]
        message = self.fix_message_init()
        message.append_pair(35, "H", header=True)  # MsgType = OrderStatusRequest
        message.append_pair(41, ID)  # ClOrdID
        return message

    def NewOrderSingle(self, data):
        order = data["order"]
        message = self.fix_message_init()
        message.append_pair(35, "D", header=True)  # MsgType = NewOrderSingle
        message.append_pair(54, 1 if order['side'] == 'buy' else 2)  # Side
        message.append_pair(38, order['quantity'])  # Quantity
        message.append_pair(44, order['price'])  # Price
        return message

    def OrderCancelRequest(self, data):
        ID = data["ID"]
        message = self.fix_message_init()
        message.append_pair(35, "F", header=True) # MsgType = OrderCancelRequest
        message.append_pair(41, ID) # ClOrdID
        return message

    def OrderModifyRequestQty(self, data):
        ID = data["ID"]
        quantity = data["quantity"]
        message = self.fix_message_init()
        message.append_pair(35, "G", header=True) # MsgType = OrderCancelReplaceRequest
        message.append_pair(41, ID) # OrigClOrdID
        message.append_pair(38, quantity) # Quantity
        return message

    def MarketDataRequest(self, data):
        depth = data["depth"]
        message = self.fix_message_init()
        message.append_pair(35, "V", header=True) # MsgType = MarketDataRequest
        message.append_pair(263, 0) # SubscriptionRequestType = Snapshot
        message.append_pair(264, depth) # MarketDepth
        return message

    def UserOrderStatusRequest(self, data):
        message = self.fix_message_init()
        message.append_pair(35, "AF", header=True) # MsgType = OrderMassStatusRequest
        message.append_pair(585, 8) # MassStatusReqType = Status for orders for a PartyID
        message.append_pair(448, self.SENDER.split('=')[1]) # PartyID
        return message

    def encode(self, data):
        msg_types_map = {
            "OrderStatusRequest": self.OrderStatusRequest,
            "NewOrderSingle": self.NewOrderSingle,
            "OrderCancelRequest": self.OrderCancelRequest,
            "OrderModifyRequestQty": self.OrderModifyRequestQty,
            "MarketDataRequest": self.MarketDataRequest,
            "UserOrderStatusRequest": self.UserOrderStatusRequest

        }
        msg_type = data["msg_type"]
        message = msg_types_map[msg_type](data)
        byte_buffer = message.encode()
        return byte_buffer

    def decode(self, data):
        pass
