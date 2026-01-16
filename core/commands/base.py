from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, Type
import threading

from ..protocol import ServiceBits

class BaseCommand(ABC):
    _instances: Dict[Type, Dict[str, Any]] = {}
    
    def __new__(cls, connection, *args, **kwargs):
        connection_id = id(connection)
        
        if cls not in cls._instances:
            cls._instances[cls] = {}
            
        if connection_id not in cls._instances[cls]:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[cls][connection_id] = instance
        else:
            instance = cls._instances[cls][connection_id]
            
        return instance
    
    def __init__(self, connection, request_type: int, response_type: int):
        if self._initialized:
            return
        
        self.connection = connection
        self.request_type = request_type
        self.response_type = response_type
        self._initialized = True
        
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        pass

class SubscriptionCommand(BaseCommand):
    def __init__(self, connection, request_type: int, response_type: int):
        super().__init__(connection, request_type, response_type)
        self._subscription_active = False
        self._subscription_id = None
        self._data_callback = None
        self._keep_alive_timer = None
        
    def subscribe(self, data_callback: Callable, keep_alive_interval: float = 1.0):
        self.connection.register_subscription_command(self)
        pass
        
    def unsubscribe(self):
        if not self._subscription_active or not self._subscription_id:
            return
            
        self.connection.send_packet(self.request_type, 0x10, packet_id=self._subscription_id)
        self._subscription_active = False
        self._stop_keep_alive()
        self.connection.unregister_subscription_command(self)
        
    def _start_keep_alive(self, interval: float):
        self._stop_keep_alive()
        
        def send_keep_alive():
            if self._subscription_active and self._subscription_id:
                self.connection.send_packet(self.request_type, ServiceBits.KEEP_ALIVE, packet_id=self._subscription_id)
                self._start_keep_alive(interval)
                
        self._keep_alive_timer = threading.Timer(interval, send_keep_alive)
        self._keep_alive_timer.daemon = True
        self._keep_alive_timer.start()
        
    def _stop_keep_alive(self):
        if self._keep_alive_timer:
            self._keep_alive_timer.cancel()
            self._keep_alive_timer = None
            
    @property
    def is_subscribed(self):
        return self._subscription_active