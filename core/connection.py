from .protocol import parse_packet, create_packet, PacketHeader
from typing import Dict, Callable, Optional
import threading
import serial

BAUDRATE = 115200
HEADER_SIZE = PacketHeader.HEADER_SIZE
SYNC = bytes([PacketHeader.SYNC1, PacketHeader.SYNC2])
_DATA_LENGTH_OFFSET = 7
_COMPACT_THRESHOLD = 4096


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
        self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05)
        self._running = True
        self._receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self._receiver_thread.start()

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
            except Exception:
                pass
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
        offset = 0
        ser = self.ser

        while self._running and ser and ser.is_open:
            try:
                chunk = ser.read(1)
                if chunk:
                    buffer.extend(chunk)
                    extra = ser.in_waiting
                    if extra:
                        buffer.extend(ser.read(extra))

                while True:
                    avail = len(buffer) - offset
                    if avail < HEADER_SIZE:
                        break

                    sync_idx = buffer.find(SYNC, offset)
                    if sync_idx < 0:
                        offset = len(buffer) - 1
                        break
                    if sync_idx != offset:
                        offset = sync_idx
                        avail = len(buffer) - offset
                        if avail < HEADER_SIZE:
                            break

                    data_length = (buffer[offset + _DATA_LENGTH_OFFSET]
                                   | (buffer[offset + _DATA_LENGTH_OFFSET + 1] << 8))
                    total = HEADER_SIZE + data_length
                    if avail < total:
                        break

                    packet_bytes = bytes(buffer[offset:offset + total])
                    packet = parse_packet(packet_bytes)
                    if packet is not None:
                        offset += total
                        self._handle_packet(packet)
                    else:
                        offset += 1

                if offset >= _COMPACT_THRESHOLD or (offset > 0 and offset == len(buffer)):
                    del buffer[:offset]
                    offset = 0

            except serial.SerialException:
                break
            except Exception:
                offset = min(offset + 1, len(buffer))

    def _handle_packet(self, packet: dict):
        packet_id = packet["packet_id"]

        with self._lock:
            handler = self._response_handlers.pop(packet_id, None)
        if handler:
            handler(packet)
            return

        packet_type = packet["packet_type"]
        type_handler = self._packet_handlers.get(packet_type)
        if type_handler:
            type_handler(packet)

    def send_packet(self, packet_type: int, service_bits: int, packet_id: Optional[int] = None,
                    data: bytes = b"", response_handler: Optional[Callable] = None,
                    timeout: float = 5.0) -> int:
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
