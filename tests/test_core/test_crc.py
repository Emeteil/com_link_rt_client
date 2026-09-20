import pytest

from core.protocol import calculate_crc


def test_known_value():
    assert calculate_crc(b"123456789") == 0x29B1


def test_empty_returns_initial_value():
    assert calculate_crc(b"") == 0xFFFF


def test_result_fits_16_bits():
    assert 0 <= calculate_crc(bytes(range(256))) <= 0xFFFF


@pytest.mark.parametrize("data", [b"a", b"abc", b"\x00\x00"])
def test_single_bit_flip_changes_crc(data):
    flipped = bytes([data[0] ^ 0x01]) + data[1:]
    assert calculate_crc(data) != calculate_crc(flipped)
