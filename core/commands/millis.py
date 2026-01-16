from .base import SubscriptionCommand
from typing import Optional, Callable
import threading
import struct

from ..protocol import ServiceBits

def _get_data(packet: dict) -> Optional[int]:
    if packet["payload"] and len(packet["payload"]) == 4:
        return struct.unpack("<I", packet["payload"])[0]
    return None

class MillisCommand(SubscriptionCommand):
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x03
        self.PACKET_TYPE_RESPONSE = 0x04
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
        self.last_data = None
        self.connection.register_handler(self.PACKET_TYPE_RESPONSE, self._handle_subscription_data)
        
    def _handle_subscription_data(self, packet):
        if not self._subscription_active:
            return
            
        if packet["service_bits"] & ServiceBits.UNSUBSCRIBED:
            self._subscription_active = False
            return
            
        if self._data_callback:
            self.last_data = _get_data(packet)
            self._data_callback(self.last_data)
        
    def execute(self, wait_response: bool = True, timeout: float = 5.0) -> Optional[int]:
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
        
    def subscribe(self, data_callback: Callable[[int], None], keep_alive_interval: float = 1.0):
        if self._subscription_active:
            return
            
        self._data_callback = data_callback
        self._subscription_active = True
        
        self._subscription_id = self.connection.send_packet(self.request_type, ServiceBits.SUBSCRIBE)
        self._start_keep_alive(keep_alive_interval)
        super().subscribe(data_callback, keep_alive_interval)