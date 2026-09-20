import struct

import pytest

from core.protocol import PacketHeader, ServiceBits, calculate_crc, create_packet


def test_header_fields_layout():
    raw = create_packet(0x07, ServiceBits.KEEP_ALIVE, 0x1234, b"xy")
    sync1, sync2, version, ptype, bits, pid, length, _ = struct.unpack(PacketHeader.STRUCT_FORMAT, raw[:PacketHeader.HEADER_SIZE])
    assert (sync1, sync2, version) == (0xAA, 0x55, 0x03)
    assert (ptype, bits, pid, length) == (0x07, ServiceBits.KEEP_ALIVE, 0x1234, 2)


def test_length_without_payload():
    assert len(create_packet(1, 0, 1)) == PacketHeader.HEADER_SIZE


def test_payload_appended_after_header():
    raw = create_packet(1, 0, 1, b"hello")
    assert raw[PacketHeader.HEADER_SIZE:] == b"hello"


def test_crc_covers_header_and_payload():
    raw = create_packet(1, 0, 1, b"hello")
    crc = struct.unpack("<H", raw[PacketHeader.HEADER_NO_CRC_SIZE:PacketHeader.HEADER_SIZE])[0]
    assert crc == calculate_crc(raw[:PacketHeader.HEADER_NO_CRC_SIZE] + b"hello")


def test_packet_id_is_little_endian():
    raw = create_packet(1, 0, 0x0102)
    assert raw[5:7] == b"\x02\x01"


@pytest.mark.parametrize("bad_id", [-1, 65536])
def test_out_of_range_packet_id_raises(bad_id):
    with pytest.raises(struct.error):
        create_packet(1, 0, bad_id)
