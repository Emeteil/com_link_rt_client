from .base import SubscriptionCommand
from typing import Optional, Callable
import threading
import struct

from ..protocol import ServiceBits

_FORMAT = "<hhhB"
_SIZE = struct.calcsize(_FORMAT)


def _get_data(packet: dict) -> Optional[dict]:
    payload = packet["payload"]
    if not payload or len(payload) != _SIZE:
        return None
    x, y, z, status = struct.unpack(_FORMAT, payload)
    return {"x": x, "y": y, "z": z, "status": status}


class MagnetometerCommand(SubscriptionCommand):
    LSB_PER_GAUSS = 3750

    STATUS_OK = 0x00
    STATUS_NOT_FOUND = 0x01
    STATUS_OVERFLOW = 0x02
    STATUS_NO_DATA = 0x03
    STATUS_BUS_STUCK = 0x04

    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x0B
        self.PACKET_TYPE_RESPONSE = 0x0C
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)

        self.last_data = None
        self.connection.register_handler(self.PACKET_TYPE_RESPONSE, self._handle_subscription_data)

    def _handle_subscription_data(self, packet):
        if not self._subscription_active:
            return

        if packet["service_bits"] & ServiceBits.UNSUBSCRIBED:
            self._subscription_active = False
            return

        data = _get_data(packet)
        if data is None:
            return
        self.last_data = data
        if self._data_callback:
            self._data_callback(data)

    def execute(self, wait_response: bool = True, timeout: float = 5.0) -> Optional[dict]:
        if self._subscription_active:
            return self.last_data

        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0)
            return None

        result = None
        response_received = threading.Event()

        def response_handler(packet):
            if packet["packet_type"] != self.PACKET_TYPE_RESPONSE:
                return

            nonlocal result
            result = _get_data(packet)
            response_received.set()

        self.connection.send_packet(self.request_type, ServiceBits.EMPTY, response_handler=response_handler)

        response_received.wait(timeout)
        return result

    def subscribe(self, data_callback: Callable[[dict], None], keep_alive_interval: float = 1.0):
        if self._subscription_active:
            return

        self._data_callback = data_callback
        self._subscription_active = True

        self._subscription_id = self.connection.send_packet(self.request_type, ServiceBits.SUBSCRIBE)
        self._start_keep_alive(keep_alive_interval)
        super().subscribe(data_callback, keep_alive_interval)
