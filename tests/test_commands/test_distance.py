import struct

from common.fake_connection import FakeConnection
from core.commands.distance import DistanceCommand
from core.protocol import ServiceBits

READINGS = [120, 0, 3999, 0xFFFF, 1, 250, 4000, 1001]
PAYLOAD = struct.pack("<8H", *READINGS)


def test_distance_execute_parses_all_sensors():
    conn = FakeConnection(response=(0x0A, PAYLOAD))
    assert DistanceCommand(conn).execute() == READINGS
    assert conn.sent == [(0x09, ServiceBits.EMPTY, b"")]


def test_distance_execute_rejects_odd_payload():
    conn = FakeConnection(response=(0x0A, b"\x01\x02\x03"))
    assert DistanceCommand(conn).execute() is None


def test_distance_subscribe_delivers_latest_values():
    conn = FakeConnection()
    cmd = DistanceCommand(conn)
    received = []
    cmd.subscribe(received.append, keep_alive_interval=60)
    try:
        assert conn.sent[0] == (0x09, ServiceBits.SUBSCRIBE, b"")
        conn.handlers[0x0A]({"packet_type": 0x0A, "service_bits": 0, "payload": PAYLOAD})
        assert received == [READINGS]
        assert cmd.execute() == READINGS
    finally:
        cmd._stop_keep_alive()


def test_distance_unsubscribed_flag_stops_subscription():
    conn = FakeConnection()
    cmd = DistanceCommand(conn)
    received = []
    cmd.subscribe(received.append, keep_alive_interval=60)
    try:
        conn.handlers[0x0A]({"packet_type": 0x0A, "service_bits": ServiceBits.UNSUBSCRIBED, "payload": b""})
        assert not cmd.is_subscribed
        assert received == []
    finally:
        cmd._stop_keep_alive()


def test_distance_unsubscribe_sends_unsubscribe():
    conn = FakeConnection()
    cmd = DistanceCommand(conn)
    cmd.subscribe(lambda values: None, keep_alive_interval=60)
    cmd.unsubscribe()
    assert conn.sent[-1] == (0x09, 0x10, b"")
    assert not cmd.is_subscribed


def test_distance_sentinels_match_firmware():
    assert DistanceCommand.NO_ECHO == 0
    assert DistanceCommand.SENSOR_ERROR == 0xFFFF
