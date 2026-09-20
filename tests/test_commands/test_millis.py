import struct

from common.fake_connection import FakeConnection
from core.commands.millis import MillisCommand
from core.protocol import ServiceBits


def test_millis_execute_parses_value():
    conn = FakeConnection(response=(0x04, struct.pack("<I", 1234)))
    assert MillisCommand(conn).execute() == 1234


def test_millis_subscribe_delivers_data():
    conn = FakeConnection()
    cmd = MillisCommand(conn)
    received = []
    cmd.subscribe(received.append, keep_alive_interval=60)
    try:
        assert conn.sent[0][1] == ServiceBits.SUBSCRIBE
        conn.handlers[0x04]({"packet_type": 0x04, "service_bits": 0, "payload": struct.pack("<I", 7)})
        assert received == [7]
    finally:
        cmd._stop_keep_alive()


def test_millis_subscribe_sends_request_with_id():
    conn = FakeConnection()
    cmd = MillisCommand(conn)
    cmd.subscribe(lambda value: None, keep_alive_interval=60)
    try:
        assert conn.sent == [(0x03, ServiceBits.SUBSCRIBE, b"")]
        assert cmd.is_subscribed
    finally:
        cmd._stop_keep_alive()


def test_millis_unsubscribe_sends_unsubscribe():
    conn = FakeConnection()
    cmd = MillisCommand(conn)
    cmd.subscribe(lambda value: None, keep_alive_interval=60)
    cmd.unsubscribe()
    assert conn.sent[-1] == (0x03, 0x10, b"")
    assert not cmd.is_subscribed


def test_millis_unsubscribed_flag_stops_subscription():
    conn = FakeConnection()
    cmd = MillisCommand(conn)
    received = []
    cmd.subscribe(received.append, keep_alive_interval=60)
    try:
        conn.handlers[0x04]({"packet_type": 0x04, "service_bits": ServiceBits.UNSUBSCRIBED, "payload": b""})
        assert not cmd.is_subscribed
        assert received == []
    finally:
        cmd._stop_keep_alive()
