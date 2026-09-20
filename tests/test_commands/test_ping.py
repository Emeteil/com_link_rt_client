from common.fake_connection import FakeConnection
from core.commands.ping import PingCommand


def test_ping_returns_latency():
    conn = FakeConnection(response=(0x02, b""))
    assert PingCommand(conn).execute() >= 0
    assert conn.sent[0][0] == 0x01


def test_ping_timeout_returns_none():
    assert PingCommand(FakeConnection()).execute(timeout=0.01) is None
