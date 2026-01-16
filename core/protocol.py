import struct
from enum import Enum

class ServiceBits(int, Enum):
    SUBSCRIBE = 0x80
    UNSUBSCRIBED = 0x40
    KEEP_ALIVE = 0x20
    UNSUBSCRIBE = 0x10
    EMPTY = 0x00

class PacketHeader:
    SYNC1 = 0xAA
    SYNC2 = 0x55
    VERSION = 0x01
    
    STRUCT_FORMAT = "<BBBBBHHH"
    HEADER_SIZE = struct.calcsize(STRUCT_FORMAT)
    
    def __init__(self, packet_type, service_bits, packet_id, data_length=0):
        self.sync1 = self.SYNC1
        self.sync2 = self.SYNC2
        self.version = self.VERSION
        self.packet_type = packet_type
        self.service_bits = service_bits
        self.packet_id = packet_id
        self.data_length = data_length
        self.crc = 0

def calculate_crc(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

def create_packet(packet_type: int, service_bits: int, packet_id: int, data: bytes = b""):
    header = PacketHeader(packet_type, service_bits, packet_id, len(data))
    
    header_bytes = struct.pack(
        PacketHeader.STRUCT_FORMAT,
        header.sync1, header.sync2, header.version,
        header.packet_type, header.service_bits,
        header.packet_id, header.data_length, 0
    )
    
    crc = calculate_crc(header_bytes[:-2])
    packet = struct.pack(
        PacketHeader.STRUCT_FORMAT,
        header.sync1, header.sync2, header.version,
        header.packet_type, header.service_bits,
        header.packet_id, header.data_length, crc
    ) + data

    return packet

def parse_packet(data: bytes):
    if len(data) < PacketHeader.HEADER_SIZE:
        return None
        
    header_data = data[:PacketHeader.HEADER_SIZE]
    fields = struct.unpack(PacketHeader.STRUCT_FORMAT, header_data)
    
    sync1, sync2, version, packet_type, service_bits, packet_id, data_length, received_crc = fields
    
    if sync1 != PacketHeader.SYNC1 or sync2 != PacketHeader.SYNC2:
        return None
        
    calculated_crc = calculate_crc(header_data[:-2])
    if received_crc != calculated_crc:
        return None
        
    payload = data[PacketHeader.HEADER_SIZE:PacketHeader.HEADER_SIZE + data_length] if data_length > 0 else b""
    
    return {
        "packet_type": packet_type,
        "service_bits": service_bits,
        "packet_id": packet_id,
        "data_length": data_length,
        "payload": payload,
        "crc_match": True
    }