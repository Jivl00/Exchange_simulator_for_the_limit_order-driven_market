from IProtocol import IProtocol


class JSONProtocol(IProtocol):
    def __init__(self):
        super().__init__()

    def encode(self, data):
        return data

    def decode(self, data):
        return data
