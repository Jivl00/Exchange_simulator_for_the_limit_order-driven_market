
class IProtocol:
    def __init__(self):
        pass

    def encode(self, data):
        """
        Encode the data into a byte buffer.
        :param data:  Data to be encoded
        :return: Byte buffer
        """
        pass

    def decode(self, data):
        """
        Decode the byte buffer into data.
        :param data: Byte buffer
        :return: Decoded data (dict)
        """
        pass