import struct

from core.protocol import PacketHeader, ServiceBits


def test_header_size():
    assert PacketHeader.HEADER_SIZE == 11
    assert PacketHeader.HEADER_SIZE == struct.calcsize(PacketHeader.STRUCT_FORMAT)
    assert PacketHeader.HEADER_NO_CRC_SIZE == PacketHeader.HEADER_SIZE - 2


def test_sync_and_version():
    assert (PacketHeader.SYNC1, PacketHeader.SYNC2) == (0xAA, 0x55)
    assert PacketHeader.VERSION == 0x03


def test_service_bits_are_distinct_flags():
    flags = [ServiceBits.SUBSCRIBE, ServiceBits.UNSUBSCRIBED, ServiceBits.KEEP_ALIVE, ServiceBits.UNSUBSCRIBE]
    combined = 0
    for flag in flags:
        assert flag & combined == 0
        combined |= flag
    assert ServiceBits.EMPTY == 0


def test_header_object_defaults():
    header = PacketHeader(packet_type=1, service_bits=0, packet_id=5)
    assert header.sync1 == PacketHeader.SYNC1
    assert header.data_length == 0
    assert header.crc == 0
