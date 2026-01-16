from .protocol import parse_packet, create_packet
from typing import Dict, Callable, Optional
import threading
import serial
import time
import struct

BAUDRATE = 115200
HEADER_SIZE = 11
SYNC_BYTE_1 = 0xAA
SYNC_BYTE_2 = 0x55

class ComLinkConnection:
    def __init__(self, port: str, timeout: float = 1.0):
        self.port = port
        self.baudrate = BAUDRATE
        self.timeout = timeout
        self.ser = None
        self._running = False
        self._receiver_thread = None
        self._packet_handlers: Dict[int, Callable] = {}
        self._response_handlers: Dict[int, Callable] = {}
        self._subscription_commands = set()
        self._next_packet_id = 1
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        
    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        self._running = True
        self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._receiver_thread.start()
        time.sleep(0.1)
        
    def disconnect(self):
        self._unsubscribe_all()
        self._running = False
        if self._receiver_thread:
            self._receiver_thread.join(timeout=1.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def _unsubscribe_all(self):
        for command in list(self._subscription_commands):
            try:
                command.unsubscribe()
            except Exception: pass
        self._subscription_commands.clear()
            
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def _get_next_packet_id(self) -> int:
        packet_id = self._next_packet_id
        self._next_packet_id = 1 if packet_id == 65535 else packet_id + 1
        return packet_id
        
    def _receiver_loop(self):
        buffer = bytearray()
        
        while self._running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)
                
                while len(buffer) >= HEADER_SIZE:
                    if buffer[0] != SYNC_BYTE_1 or buffer[1] != SYNC_BYTE_2:
                        buffer.pop(0)
                        continue
                        
                    if len(buffer) < HEADER_SIZE:
                        break
                    
                    try:
                        header_data = bytes(buffer[:HEADER_SIZE])
                        fields = struct.unpack("<BBBBBHHH", header_data)
                        data_length = fields[6]
                        
                        total_length = HEADER_SIZE + data_length
                        if len(buffer) < total_length:
                            break
                            
                        packet_data = bytes(buffer[:total_length])
                        packet = parse_packet(packet_data)
                        
                        if packet:
                            self._handle_packet(packet)
                            buffer = buffer[total_length:]
                        else:
                            buffer.pop(0)
                    except Exception:
                        buffer.pop(0)
                        
            except Exception:
                time.sleep(0.01)
                
    def _handle_packet(self, packet: dict):
        packet_id = packet["packet_id"]
        
        with self._lock:
            if packet_id in self._response_handlers:
                handler = self._response_handlers.pop(packet_id, None)
                if handler:
                    handler(packet)
                    return
        
        packet_type = packet["packet_type"]
        if packet_type in self._packet_handlers:
            self._packet_handlers[packet_type](packet)
            
    def send_packet(self, packet_type: int, service_bits: int, packet_id: Optional[int] = None, data: bytes = b"", response_handler: Optional[Callable] = None, timeout: float = 5.0) -> int:
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Соединение не установлено")
        
        if packet_id is None:
            packet_id = self._get_next_packet_id()
        packet = create_packet(packet_type, service_bits, packet_id, data)
        
        if response_handler:
            with self._lock:
                self._response_handlers[packet_id] = response_handler
            
            def remove_handler():
                with self._lock:
                    if packet_id in self._response_handlers:
                        self._response_handlers.pop(packet_id, None)
            
            timer = threading.Timer(timeout, remove_handler)
            timer.daemon = True
            timer.start()
            
        with self._write_lock:
            self.ser.write(packet)
        
        return packet_id
    
    def register_subscription_command(self, command):
        self._subscription_commands.add(command)
    
    def unregister_subscription_command(self, command):
        self._subscription_commands.discard(command)
        
    def register_handler(self, packet_type: int, handler: Callable):
        self._packet_handlers[packet_type] = handler
        
    def unregister_handler(self, packet_type: int):
        self._packet_handlers.pop(packet_type, None)