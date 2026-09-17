from .base import BaseCommand
from typing import Optional
import threading
import struct

from ..protocol import ServiceBits

def _get_data(packet: dict) -> Optional[dict]:
    if packet["payload"] and len(packet["payload"]) == 21:
        build_date, build_time = struct.unpack("<12s9s", packet["payload"])
        return {
            "build_date": build_date.rstrip(b"\x00").decode("ascii"),
            "build_time": build_time.rstrip(b"\x00").decode("ascii"),
        }
    return None

class VersionCommand(BaseCommand):
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x05
        self.PACKET_TYPE_RESPONSE = 0x06
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)

    def execute(self, wait_response: bool = True, timeout: float = 5.0) -> Optional[dict]:
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
