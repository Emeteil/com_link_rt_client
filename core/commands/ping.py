from .base import BaseCommand
from typing import Optional
import threading
import time

from ..protocol import ServiceBits

class PingCommand(BaseCommand):    
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x01
        self.PACKET_TYPE_RESPONSE = 0x02
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
    def execute(self, wait_response: bool = True, timeout: float = 5.0) -> Optional[float]:
        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0)
            return None
            
        start_time = time.time()
        response_received = threading.Event()
        
        def response_handler(packet):
            if packet["packet_type"] != self.PACKET_TYPE_RESPONSE:
                return
            
            nonlocal response_received
            response_received.set()
            
        self.connection.send_packet(self.request_type, ServiceBits.EMPTY, response_handler=response_handler)
        
        response_received.wait(timeout)
        
        if not response_received.is_set():
            return None
        
        return (time.time() - start_time) * 1000