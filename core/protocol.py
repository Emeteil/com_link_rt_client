import struct
from enum import Enum

class ServiceBits(int, Enum):
    SUBSCRIBE = 0x80
    UNSUBSCRIBED = 0x40
    KEEP_ALIVE = 0x20
    UNSUBSCRIBE = 0x10
    NO_REPLY = 0x08
    EMPTY = 0x00


def _build_crc_table():
    table = [0] * 256
    for i in range(256):
        c = (i << 8) & 0xFFFF
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if (c & 0x8000) else ((c << 1) & 0xFFFF)
        table[i] = c
    return tuple(table)

_CRC_TABLE = _build_crc_table()


def _crc_update(crc: int, data: bytes) -> int:
    table = _CRC_TABLE
    for b in data:
        crc = ((crc << 8) & 0xFFFF) ^ table[((crc >> 8) ^ b) & 0xFF]
    return crc


def calculate_crc(data: bytes) -> int:
    return _crc_update(0xFFFF, data)


class PacketHeader:
    SYNC1 = 0xAA
    SYNC2 = 0x55
    VERSION = 0x02

    STRUCT_FORMAT = "<BBBBBHHH"
    HEADER_SIZE = struct.calcsize(STRUCT_FORMAT)
    HEADER_NO_CRC_SIZE = HEADER_SIZE - 2

    def __init__(self, packet_type, service_bits, packet_id, data_length=0):
        self.sync1 = self.SYNC1
        self.sync2 = self.SYNC2
        self.version = self.VERSION
        self.packet_type = packet_type
        self.service_bits = service_bits
        self.packet_id = packet_id
        self.data_length = data_length
        self.crc = 0


def create_packet(packet_type: int, service_bits: int, packet_id: int, data: bytes = b"") -> bytes:
    data_length = len(data)
    header_no_crc = struct.pack(
        "<BBBBBHH",
        PacketHeader.SYNC1, PacketHeader.SYNC2, PacketHeader.VERSION,
        packet_type, service_bits, packet_id, data_length,
    )
    crc = _crc_update(0xFFFF, header_no_crc)
    if data_length:
        crc = _crc_update(crc, data)
    return header_no_crc + struct.pack("<H", crc) + data


def parse_packet(data: bytes):
    if len(data) < PacketHeader.HEADER_SIZE:
        return None

    header_data = data[:PacketHeader.HEADER_SIZE]
    fields = struct.unpack(PacketHeader.STRUCT_FORMAT, header_data)
    sync1, sync2, version, packet_type, service_bits, packet_id, data_length, received_crc = fields

    if sync1 != PacketHeader.SYNC1 or sync2 != PacketHeader.SYNC2:
        return None
    if len(data) < PacketHeader.HEADER_SIZE + data_length:
        return None

    payload = data[PacketHeader.HEADER_SIZE:PacketHeader.HEADER_SIZE + data_length]

    crc = _crc_update(0xFFFF, header_data[:PacketHeader.HEADER_NO_CRC_SIZE])
    if data_length:
        crc = _crc_update(crc, payload)
    if crc != received_crc:
        return None

    return {
        "packet_type": packet_type,
        "service_bits": service_bits,
        "packet_id": packet_id,
        "data_length": data_length,
        "payload": bytes(payload),
        "crc_match": True,
    }
