from .base import BaseCommand
from typing import Optional
import threading
import struct

from ..protocol import ServiceBits

_HEADER = "<4B4iI4H7B2I2H2B"
_HEADER_SIZE = struct.calcsize(_HEADER)
_SATELLITE = "<BbHB"
_SATELLITE_SIZE = struct.calcsize(_SATELLITE)
_AGE_NEVER = 0xFFFFFFFF

_FLAG_ALIVE = 0x01
_FLAG_POSITION_VALID = 0x02
_FLAG_TIME_VALID = 0x04
_FLAG_DATE_VALID = 0x08


def _dop(centi: int) -> Optional[float]:
    return centi / 100 if centi else None


def _age(value: int) -> Optional[int]:
    return None if value == _AGE_NEVER else value


def _get_data(packet: dict) -> Optional[dict]:
    payload = packet["payload"]
    if not payload or len(payload) < _HEADER_SIZE:
        return None

    (flags, fix_quality, fix_type, satellites_used,
     lat, lon, alt_cm, geoid_cm,
     speed_mm_s, course_cdeg, hdop, pdop, vdop,
     year, month, day, hour, minute, second, centisecond,
     fix_age, sentence_age, sentences_ok, checksum_errors,
     in_view, count) = struct.unpack_from(_HEADER, payload)

    if len(payload) != _HEADER_SIZE + count * _SATELLITE_SIZE:
        return None

    satellites = []
    for i in range(count):
        prn, elevation, azimuth, snr = struct.unpack_from(_SATELLITE, payload, _HEADER_SIZE + i * _SATELLITE_SIZE)
        satellites.append({
            "prn": prn,
            "elevation": None if elevation < 0 else elevation,
            "azimuth": None if azimuth == 0xFFFF else azimuth,
            "snr": snr or None,
        })

    position_valid = bool(flags & _FLAG_POSITION_VALID)
    return {
        "alive": bool(flags & _FLAG_ALIVE),
        "position_valid": position_valid,
        "fix_quality": fix_quality,
        "fix_type": fix_type,
        "satellites_used": satellites_used,
        "satellites_in_view": in_view,
        "latitude": lat / 1e7 if position_valid else None,
        "longitude": lon / 1e7 if position_valid else None,
        "altitude_m": alt_cm / 100 if position_valid else None,
        "geoid_separation_m": geoid_cm / 100 if position_valid else None,
        "speed_m_s": speed_mm_s / 1000,
        "course_deg": course_cdeg / 100,
        "hdop": _dop(hdop),
        "pdop": _dop(pdop),
        "vdop": _dop(vdop),
        "date": f"20{year:02d}-{month:02d}-{day:02d}" if flags & _FLAG_DATE_VALID else None,
        "time": f"{hour:02d}:{minute:02d}:{second:02d}.{centisecond:02d}" if flags & _FLAG_TIME_VALID else None,
        "fix_age_ms": _age(fix_age),
        "sentence_age_ms": _age(sentence_age),
        "sentences_ok": sentences_ok,
        "checksum_errors": checksum_errors,
        "satellites": satellites,
    }


class GpsCommand(BaseCommand):
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x0D
        self.PACKET_TYPE_RESPONSE = 0x0E
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        self.last_data = None

    def execute(self, wait_response: bool = True, timeout: float = 2.0) -> Optional[dict]:
        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0)
            return None

        result = None
        response_received = threading.Event()

        def response_handler(packet):
            if packet["packet_type"] != self.PACKET_TYPE_RESPONSE:
                return

            nonlocal result
            result = _get_data(packet)
            response_received.set()

        self.connection.send_packet(self.request_type, ServiceBits.EMPTY, response_handler=response_handler)

        response_received.wait(timeout)
        if result is not None:
            self.last_data = result
        return result
