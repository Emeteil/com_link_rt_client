import pytest

from core.protocol import PacketHeader, ServiceBits, create_packet, parse_packet


@pytest.mark.parametrize("payload", [b"", b"\x01", b"\x01\x02\x03", bytes(range(200))])
def test_roundtrip(payload):
    packet = parse_packet(create_packet(0x07, ServiceBits.SUBSCRIBE, 42, payload))
    assert packet["packet_type"] == 0x07
    assert packet["service_bits"] == ServiceBits.SUBSCRIBE
    assert packet["packet_id"] == 42
    assert packet["data_length"] == len(payload)
    assert packet["payload"] == payload
    assert packet["crc_match"] is True


def test_extra_trailing_bytes_are_ignored():
    packet = parse_packet(create_packet(1, 0, 1, b"ab") + b"garbage")
    assert packet["payload"] == b"ab"


def test_empty_input():
    assert parse_packet(b"") is None


def test_short_input():
    assert parse_packet(b"\xaa\x55") is None


@pytest.mark.parametrize("index", [0, 1])
def test_bad_sync(index):
    raw = bytearray(create_packet(1, 0, 1))
    raw[index] ^= 0xFF
    assert parse_packet(bytes(raw)) is None


def test_bad_crc_in_payload():
    raw = bytearray(create_packet(1, 0, 1, b"abc"))
    raw[-1] ^= 0xFF
    assert parse_packet(bytes(raw)) is None


def test_bad_crc_in_header():
    raw = bytearray(create_packet(1, 0, 1, b"abc"))
    raw[3] ^= 0x01
    assert parse_packet(bytes(raw)) is None


def test_truncated_payload():
    raw = create_packet(1, 0, 1, b"abcdef")
    assert parse_packet(raw[:-1]) is None


def test_header_only_with_declared_payload_is_rejected():
    raw = create_packet(1, 0, 1, b"abcdef")
    assert parse_packet(raw[:PacketHeader.HEADER_SIZE]) is None
