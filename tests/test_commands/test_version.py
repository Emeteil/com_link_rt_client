import struct

from common.fake_connection import FakeConnection
from core.commands.version import VersionCommand


def test_version_parses_payload():
    payload = struct.pack("<12s9s", b"Jan  1 2025", b"12:34:56")
    conn = FakeConnection(response=(0x06, payload))
    assert VersionCommand(conn).execute() == {"build_date": "Jan  1 2025", "build_time": "12:34:56"}


def test_version_bad_payload_returns_none():
    assert VersionCommand(FakeConnection(response=(0x06, b"abc"))).execute() is None
