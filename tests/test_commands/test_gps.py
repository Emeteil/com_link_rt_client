import struct

from common.fake_connection import FakeConnection
from core.commands.gps import GpsCommand
from core.protocol import ServiceBits

HEADER = "<4B4iI4H7B2I2H2B"
NEVER = 0xFFFFFFFF


def build(flags=0x0F, satellites=(), fix_age=120, sentence_age=40):
    header = struct.pack(
        HEADER,
        flags, 1, 3, 8,
        550187242, 829113150, 15230, -2510,
        772, 8440, 92, 165, 137,
        26, 10, 18, 12, 35, 19, 0,
        fix_age, sentence_age, 5, 0,
        len(satellites), len(satellites),
    )
    return header + b"".join(struct.pack("<BbHB", *s) for s in satellites)


def test_gps_header_is_53_bytes_like_firmware():
    assert struct.calcsize(HEADER) == 53


def test_gps_parses_full_fix():
    payload = build(satellites=[(4, 45, 120, 38), (9, 10, 45, 0), (17, -1, 0xFFFF, 0)])
    conn = FakeConnection(response=(0x0E, payload))

    info = GpsCommand(conn).execute()

    assert conn.sent == [(0x0D, ServiceBits.EMPTY, b"")]
    assert info["alive"] is True
    assert info["position_valid"] is True
    assert info["latitude"] == 55.0187242
    assert info["longitude"] == 82.911315
    assert info["altitude_m"] == 152.3
    assert info["geoid_separation_m"] == -25.1
    assert info["speed_m_s"] == 0.772
    assert info["course_deg"] == 84.4
    assert (info["hdop"], info["pdop"], info["vdop"]) == (0.92, 1.65, 1.37)
    assert info["date"] == "2026-10-18"
    assert info["time"] == "12:35:19.00"
    assert info["fix_type"] == 3
    assert info["satellites_used"] == 8
    assert info["fix_age_ms"] == 120
    assert info["satellites"] == [
        {"prn": 4, "elevation": 45, "azimuth": 120, "snr": 38},
        {"prn": 9, "elevation": 10, "azimuth": 45, "snr": None},
        {"prn": 17, "elevation": None, "azimuth": None, "snr": None},
    ]


def test_gps_without_fix_hides_position_and_unknown_ages():
    conn = FakeConnection(response=(0x0E, build(flags=0x01, fix_age=NEVER, sentence_age=NEVER)))

    info = GpsCommand(conn).execute()

    assert info["alive"] is True
    assert info["latitude"] is None
    assert info["date"] is None
    assert info["time"] is None
    assert info["fix_age_ms"] is None
    assert info["sentence_age_ms"] is None


def test_gps_rejects_truncated_satellite_list():
    payload = build(satellites=[(4, 45, 120, 38)])[:-2]
    assert GpsCommand(FakeConnection(response=(0x0E, payload))).execute() is None


def test_gps_no_response_returns_none():
    assert GpsCommand(FakeConnection()).execute(timeout=0.01) is None
