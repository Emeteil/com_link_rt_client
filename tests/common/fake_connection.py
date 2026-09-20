class FakeConnection:
    def __init__(self, response=None):
        self.response = response
        self.sent = []
        self.handlers = {}

    def register_handler(self, packet_type, handler):
        self.handlers[packet_type] = handler

    def register_subscription_command(self, command):
        pass

    def unregister_subscription_command(self, command):
        pass

    def send_packet(self, packet_type, service_bits, packet_id=1, data=b"", response_handler=None):
        self.sent.append((packet_type, service_bits, data))
        if response_handler and self.response:
            resp_type, payload = self.response
            response_handler({"packet_type": resp_type, "service_bits": 0,
                              "packet_id": packet_id, "payload": payload})
        return packet_id
