import struct

import pytest

from common.fake_connection import FakeConnection
from core.commands.motors import MotorsCommand


def test_motors_move_forward_payload():
    conn = FakeConnection()
    assert MotorsCommand(conn).move_forward(speed=100, wait_response=False) is True
    packet_type, _, data = conn.sent[0]
    assert packet_type == 0x07
    assert data == bytes.fromhex("03 03 01 01 64 64")


def test_motors_stop_all_waits_for_response():
    conn = FakeConnection(response=(0x08, b""))
    assert MotorsCommand(conn).stop_all() is True


def test_motors_no_response_returns_false():
    assert MotorsCommand(FakeConnection()).stop_all(timeout=0.01) is False


@pytest.mark.parametrize("call", [
    lambda m: m.set_speed(MotorsCommand.MOTOR_BOTH, 256, 0),
    lambda m: m.set_speed(0x00, 10, 10),
    lambda m: m.set_direction(MotorsCommand.MOTOR_BOTH, 9, 0),
    lambda m: m.set_differential(10, 10, direction_left=MotorsCommand.DIRECTION_STOP),
])
def test_motors_validation(call):
    with pytest.raises(ValueError):
        call(MotorsCommand(FakeConnection()))


def test_motors_speed_conversion():
    m = MotorsCommand(FakeConnection())
    assert m.speed_to_percentage(255) == 100.0
    assert m.percentage_to_speed(50) == 127
    assert m.percentage_to_speed(-5) == 0
    assert m.percentage_to_speed(500) == 255
