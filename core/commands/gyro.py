from .base import SubscriptionCommand
from typing import Optional, Callable, Tuple, Dict, Any
import threading
import struct

from ..protocol import ServiceBits

def _parse_gyro_data(packet: dict) -> Optional[Dict[str, Any]]:
    if not packet["payload"] or len(packet["payload"]) != 14:
        return None
        
    try:
        accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temperature = struct.unpack("<hhhhhhh", packet["payload"])
        
        return {
            "accel": (accel_x, accel_y, accel_z),
            "gyro": (gyro_x, gyro_y, gyro_z),
            "temperature": temperature,
            "mode": packet["service_bits"] & 0x0F,
            "raw_packet": packet
        }
    except struct.error:
        return None

class GyroCommand(SubscriptionCommand):
    GYRO_RAW = 0x00
    GYRO_CALIBRATE = 0x01
    GYRO_CALIBRATED = 0x02
    GYRO_FILTERED = 0x03
    GYRO_CALIBRATED_FILTERED = 0x04
    
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x07
        self.PACKET_TYPE_RESPONSE = 0x08
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
        self.last_data: Optional[Dict[str, Any]] = None
        self._calibration_callback: Optional[Callable[[bool], None]] = None
        self._calibration_timeout: Optional[threading.Timer] = None
        
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
            data = _parse_gyro_data(packet)
            if data:
                self.last_data = data
                self._data_callback(data)
        
    def execute(self, mode: int = GYRO_RAW, wait_response: bool = True, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        
        if not wait_response:
            self.connection.send_packet(self.request_type, mode, packet_id=0)
            return None
            
        result = None
        response_received = threading.Event()
        
        def response_handler(packet):
            if packet["packet_type"] != self.PACKET_TYPE_RESPONSE:
                return

            nonlocal result
            result = _parse_gyro_data(packet)
            response_received.set()
        
        self.connection.send_packet(
            self.request_type, 
            mode, 
            response_handler=response_handler
        )
        
        response_received.wait(timeout)
        return result
        
    def calibrate(self, callback: Optional[Callable[[bool], None]] = None, timeout: float = 2.0):
        self._calibration_callback = callback
        
        def calibration_timeout():
            if self._calibration_callback:
                self._calibration_callback(False)
            self._calibration_callback = None
            
        self._calibration_timeout = threading.Timer(timeout, calibration_timeout)
        self._calibration_timeout.daemon = True
        self._calibration_timeout.start()
        
        self.connection.send_packet(self.request_type, self.GYRO_CALIBRATE, packet_id=0)
        
    def subscribe(self, data_callback: Callable[[Dict[str, Any]], None], mode: int = GYRO_CALIBRATED_FILTERED, keep_alive_interval: float = 0.5) -> bool:
        if self._subscription_active:
            return False
            
        self._data_callback = data_callback
        self._subscription_active = True
        
        service_bits = ServiceBits.SUBSCRIBE | mode
        
        self._subscription_id = self.connection.send_packet(self.request_type, service_bits)
        self._start_keep_alive(keep_alive_interval)
        
        self.connection.register_subscription_command(self)
        return True
        
    def get_acceleration(self, data: Optional[Dict[str, Any]] = None) -> Tuple[float, float, float]:
        data = data or self.last_data
        if not data or "accel" not in data:
            return (0.0, 0.0, 0.0)
            
        accel_x, accel_y, accel_z = data["accel"]
        scale = 16384.0
        
        return (accel_x / scale, accel_y / scale, accel_z / scale)
        
    def get_rotation(self, data: Optional[Dict[str, Any]] = None) -> Tuple[float, float, float]:
        data = data or self.last_data
        if not data or "gyro" not in data:
            return (0.0, 0.0, 0.0)
            
        gyro_x, gyro_y, gyro_z = data["gyro"]
        scale = 131.0
        
        return (gyro_x / scale, gyro_y / scale, gyro_z / scale)
        
    def get_temperature(self, data: Optional[Dict[str, Any]] = None) -> float:
        data = data or self.last_data
        if not data or "temperature" not in data:
            return 0.0
            
        return data["temperature"] / 340.0 + 36.53
        
    def is_calibrating(self) -> bool:
        return self._calibration_timeout is not None
        
    def _stop_keep_alive(self):
        super()._stop_keep_alive()
        
        if self._calibration_timeout:
            self._calibration_timeout.cancel()
            self._calibration_timeout = None