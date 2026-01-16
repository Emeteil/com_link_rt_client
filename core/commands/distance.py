from .base import SubscriptionCommand
from typing import Optional, Callable
import threading
import struct

from ..protocol import ServiceBits

def _parse_distance_data(packet: dict) -> Optional[int]:
    if not packet["payload"] or len(packet["payload"]) != 4:
        return None
        
    try:
        return struct.unpack("<I", packet["payload"])[0]
    except struct.error:
        return None

class DistanceCommand(SubscriptionCommand):
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x05
        self.PACKET_TYPE_RESPONSE = 0x06
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
        self.last_distance: Optional[int] = None
        self.connection.register_handler(self.PACKET_TYPE_RESPONSE, self._handle_response)
        
    def _handle_response(self, packet: dict):
        service_bits = packet["service_bits"]
        
        if service_bits & ServiceBits.UNSUBSCRIBED:
            self._subscription_active = False
            self._stop_keep_alive()
            self.connection.unregister_subscription_command(self)
            return
            
        if not self._subscription_active:
            return
            
        if self._data_callback:
            distance = _parse_distance_data(packet)
            if distance is not None:
                self.last_distance = distance
                self._data_callback(distance)
        
    def execute(self, wait_response: bool = True, timeout: float = 5.0) -> Optional[int]:
        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0)
            return None
            
        result = None
        response_received = threading.Event()
        
        def response_handler(packet):
            if packet["packet_type"] != self.PACKET_TYPE_RESPONSE:
                return

            nonlocal result
            result = _parse_distance_data(packet)
            response_received.set()
        
        self.connection.send_packet(
            self.request_type, 
            ServiceBits.EMPTY, 
            response_handler=response_handler
        )
        
        response_received.wait(timeout)
        return result
        
    def subscribe(self, data_callback: Callable[[int], None], keep_alive_interval: float = 1.0) -> bool:
        if self._subscription_active:
            return False
            
        self._data_callback = data_callback
        self._subscription_active = True
        
        service_bits = ServiceBits.SUBSCRIBE
        
        self._subscription_id = self.connection.send_packet(self.request_type, service_bits)
        self._start_keep_alive(keep_alive_interval)
        
        self.connection.register_subscription_command(self)
        return True
        
    def get_distance_cm(self, distance: Optional[int] = None) -> Optional[float]:
        dist = distance if distance is not None else self.last_distance
        if dist is None:
            return None
        return float(dist)
        
    def get_distance_mm(self, distance: Optional[int] = None) -> Optional[float]:
        dist = self.get_distance_cm(distance)
        if dist is None:
            return None
        return dist * 10.0
        
    def get_distance_m(self, distance: Optional[int] = None) -> Optional[float]:
        dist = self.get_distance_cm(distance)
        if dist is None:
            return None
        return dist / 100.0
        
    def get_distance_inches(self, distance: Optional[int] = None) -> Optional[float]:
        dist = self.get_distance_cm(distance)
        if dist is None:
            return None
        return dist / 2.54
        
    def get_distance_feet(self, distance: Optional[int] = None) -> Optional[float]:
        inches = self.get_distance_inches(distance)
        if inches is None:
            return None
        return inches / 12.0
        
    def is_valid_distance(self, distance: Optional[int] = None, max_distance_cm: int = 400) -> bool:
        dist = distance if distance is not None else self.last_distance
        if dist is None:
            return False
        return 0 < dist <= max_distance_cm
        
    def distance_to_percentage(self, distance: Optional[int] = None, min_cm: int = 2, max_cm: int = 400) -> Optional[float]:
        dist = distance if distance is not None else self.last_distance
        if dist is None or dist < min_cm or dist > max_cm:
            return None
            
        normalized = (dist - min_cm) / (max_cm - min_cm)
        return max(0.0, min(1.0, 1.0 - normalized))