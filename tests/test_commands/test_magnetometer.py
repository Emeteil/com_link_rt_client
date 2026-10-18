import struct

from common.fake_connection import FakeConnection
from core.commands.magnetometer import MagnetometerCommand
from core.protocol import ServiceBits

PAYLOAD = struct.pack("<hhhB", 1000, -2000, 300, MagnetometerCommand.STATUS_OK)
EXPECTED = {"x": 1000, "y": -2000, "z": 300, "status": 0}


def test_magnetometer_execute_parses_sample():
    conn = FakeConnection(response=(0x0C, PAYLOAD))
    assert MagnetometerCommand(conn).execute() == EXPECTED
    assert conn.sent == [(0x0B, ServiceBits.EMPTY, b"")]


def test_magnetometer_rejects_wrong_size():
    conn = FakeConnection(response=(0x0C, b"\x00" * 6))
    assert MagnetometerCommand(conn).execute() is None


def test_magnetometer_subscribe_delivers_samples():
    conn = FakeConnection()
    cmd = MagnetometerCommand(conn)
    received = []
    cmd.subscribe(received.append, keep_alive_interval=60)
    try:
        assert conn.sent[0] == (0x0B, ServiceBits.SUBSCRIBE, b"")
        conn.handlers[0x0C]({"packet_type": 0x0C, "service_bits": 0, "payload": PAYLOAD})
        assert received == [EXPECTED]
        assert cmd.execute() == EXPECTED
    finally:
        cmd._stop_keep_alive()


def test_magnetometer_unsubscribed_flag_stops_subscription():
    conn = FakeConnection()
    cmd = MagnetometerCommand(conn)
    cmd.subscribe(lambda data: None, keep_alive_interval=60)
    try:
        conn.handlers[0x0C]({"packet_type": 0x0C, "service_bits": ServiceBits.UNSUBSCRIBED, "payload": b""})
        assert not cmd.is_subscribed
    finally:
        cmd._stop_keep_alive()


def test_magnetometer_constants_match_firmware():
    assert MagnetometerCommand.LSB_PER_GAUSS == 3750
    assert MagnetometerCommand.STATUS_BUS_STUCK == 4
