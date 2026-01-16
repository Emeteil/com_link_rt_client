from .base import BaseCommand
from typing import Optional
import threading
import struct

from ..protocol import ServiceBits

class MotorsCommand(BaseCommand):
    COMMAND_SET_SPEED = 0x01
    COMMAND_SET_DIRECTION = 0x02
    COMMAND_SET_BOTH = 0x03
    COMMAND_STOP_ALL = 0x04
    COMMAND_SET_DIFFERENTIAL = 0x05
    
    DIRECTION_STOP = 0x00
    DIRECTION_FORWARD = 0x01
    DIRECTION_BACKWARD = 0x02
    DIRECTION_BRAKE = 0x03
    
    MOTOR_LEFT = 0x01 # ..0001
    MOTOR_RIGHT = 0x02 # ..0010
    MOTOR_BOTH = 0x03 # ..0011
    
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x0B
        self.PACKET_TYPE_RESPONSE = 0x0C
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
        self.connection.register_handler(self.PACKET_TYPE_RESPONSE, self._handle_response)
        self._last_response = None
        
    def _handle_response(self, packet: dict):
        self._last_response = packet
        
    def _create_command_data(self, command_type: int, motor_mask: int, direction1: int = DIRECTION_STOP, direction2: int = DIRECTION_STOP, speed1: int = 0, speed2: int = 0) -> bytes:
        return struct.pack('<BBBBBB', command_type, motor_mask, direction1, direction2, speed1, speed2)
    
    def set_speed(self, motor_mask: int, speed_left: int = 0, speed_right: int = 0, wait_response: bool = True, timeout: float = 1.0) -> bool:
        if not (0 <= speed_left <= 255) or not (0 <= speed_right <= 255):
            raise ValueError("Скорость должна быть в диапазоне от 0 до 255.")
        
        if motor_mask not in [self.MOTOR_LEFT, self.MOTOR_RIGHT, self.MOTOR_BOTH]:
            raise ValueError("Маска моторов недопустима.")
        
        return self._send_command(
            command_type=self.COMMAND_SET_SPEED,
            motor_mask=motor_mask,
            speed1=speed_left,
            speed2=speed_right,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def set_direction(self, motor_mask: int, direction_left: int = DIRECTION_STOP, direction_right: int = DIRECTION_STOP, wait_response: bool = True, timeout: float = 1.0) -> bool:
        valid_directions = [self.DIRECTION_STOP, self.DIRECTION_FORWARD, 
                           self.DIRECTION_BACKWARD, self.DIRECTION_BRAKE]
        
        if direction_left not in valid_directions or direction_right not in valid_directions:
            raise ValueError("Недопустимое значение направления")
        
        if motor_mask not in [self.MOTOR_LEFT, self.MOTOR_RIGHT, self.MOTOR_BOTH]:
            raise ValueError("Маска моторов недопустима.")
        
        return self._send_command(
            command_type=self.COMMAND_SET_DIRECTION,
            motor_mask=motor_mask,
            direction1=direction_left,
            direction2=direction_right,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def set_both(self, motor_mask: int, direction_left: int = DIRECTION_STOP, direction_right: int = DIRECTION_STOP, speed_left: int = 0, speed_right: int = 0, wait_response: bool = True, timeout: float = 1.0) -> bool:
        if not (0 <= speed_left <= 255) or not (0 <= speed_right <= 255):
            raise ValueError("Скорость должна быть в диапазоне от 0 до 255.")
        
        valid_directions = [self.DIRECTION_STOP, self.DIRECTION_FORWARD, 
                           self.DIRECTION_BACKWARD, self.DIRECTION_BRAKE]
        
        if direction_left not in valid_directions or direction_right not in valid_directions:
            raise ValueError("Недопустимое значение направления")
        
        if motor_mask not in [self.MOTOR_LEFT, self.MOTOR_RIGHT, self.MOTOR_BOTH]:
            raise ValueError("Маска моторов недопустима.")
        
        return self._send_command(
            command_type=self.COMMAND_SET_BOTH,
            motor_mask=motor_mask,
            direction1=direction_left,
            direction2=direction_right,
            speed1=speed_left,
            speed2=speed_right,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def stop_all(self, wait_response: bool = True, timeout: float = 1.0) -> bool:
        command_data = self._create_command_data(
            command_type=self.COMMAND_STOP_ALL,
            motor_mask=self.MOTOR_BOTH
        )
        
        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0, data=command_data)
            return True
        
        result = False
        response_received = threading.Event()
        
        def response_handler(packet: dict):
            nonlocal result
            if packet["packet_type"] == self.PACKET_TYPE_RESPONSE:
                result = True
                response_received.set()
        
        self.connection.send_packet(
            self.request_type,
            ServiceBits.EMPTY,
            data=command_data,
            response_handler=response_handler
        )
        
        response_received.wait(timeout)
        return result
    
    def set_differential(self, speed_left: int, speed_right: int, direction_left: int = DIRECTION_FORWARD, direction_right: int = DIRECTION_FORWARD, wait_response: bool = True, timeout: float = 1.0) -> bool:
        if not (0 <= speed_left <= 255) or not (0 <= speed_right <= 255):
            raise ValueError("Скорость должна быть в диапазоне от 0 до 255.")
        
        valid_directions = [self.DIRECTION_FORWARD, self.DIRECTION_BACKWARD]
        
        if direction_left not in valid_directions or direction_right not in valid_directions:
            raise ValueError("Направление должно быть DIRECTION_FORWARD или DIRECTION_BACKWARD для дифференциального управления.")
        
        return self._send_command(
            command_type=self.COMMAND_SET_DIFFERENTIAL,
            motor_mask=self.MOTOR_BOTH,
            direction1=direction_left,
            direction2=direction_right,
            speed1=speed_left,
            speed2=speed_right,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def _send_command(self, command_type: int, motor_mask: int, direction1: int = DIRECTION_STOP, direction2: int = DIRECTION_STOP, speed1: int = 0, speed2: int = 0, wait_response: bool = True, timeout: float = 1.0) -> bool:
        command_data = self._create_command_data(
            command_type=command_type,
            motor_mask=motor_mask,
            direction1=direction1,
            direction2=direction2,
            speed1=speed1,
            speed2=speed2
        )
        
        if not wait_response:
            self.connection.send_packet(self.request_type, ServiceBits.EMPTY, packet_id=0, data=command_data)
            return True
        
        result = False
        response_received = threading.Event()
        
        def response_handler(packet: dict):
            nonlocal result
            if packet["packet_type"] == self.PACKET_TYPE_RESPONSE:
                result = True
                response_received.set()
        
        self.connection.send_packet(
            self.request_type,
            ServiceBits.EMPTY,
            data=command_data,
            response_handler=response_handler
        )
        
        response_received.wait(timeout)
        return result
    
    def execute(self, command_type: int, motor_mask: int, direction_left: int = DIRECTION_STOP, direction_right: int = DIRECTION_STOP, speed_left: int = 0, speed_right: int = 0, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self._send_command(
            command_type=command_type,
            motor_mask=motor_mask,
            direction1=direction_left,
            direction2=direction_right,
            speed1=speed_left,
            speed2=speed_right,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def move_forward(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_both(
            motor_mask=self.MOTOR_BOTH,
            direction_left=self.DIRECTION_FORWARD,
            direction_right=self.DIRECTION_FORWARD,
            speed_left=speed,
            speed_right=speed,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def move_backward(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_both(
            motor_mask=self.MOTOR_BOTH,
            direction_left=self.DIRECTION_BACKWARD,
            direction_right=self.DIRECTION_BACKWARD,
            speed_left=speed,
            speed_right=speed,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def turn_left(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_differential(
            speed_left=speed,
            speed_right=speed,
            direction_left=self.DIRECTION_BACKWARD,
            direction_right=self.DIRECTION_FORWARD,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def turn_right(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_differential(
            speed_left=speed,
            speed_right=speed,
            direction_left=self.DIRECTION_FORWARD,
            direction_right=self.DIRECTION_BACKWARD,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def rotate_left(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_both(
            motor_mask=self.MOTOR_BOTH,
            direction_left=self.DIRECTION_BACKWARD,
            direction_right=self.DIRECTION_FORWARD,
            speed_left=speed,
            speed_right=speed,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def rotate_right(self, speed: int = 150, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_both(
            motor_mask=self.MOTOR_BOTH,
            direction_left=self.DIRECTION_FORWARD,
            direction_right=self.DIRECTION_BACKWARD,
            speed_left=speed,
            speed_right=speed,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def brake(self, wait_response: bool = True, timeout: float = 1.0) -> bool:
        return self.set_direction(
            motor_mask=self.MOTOR_BOTH,
            direction_left=self.DIRECTION_BRAKE,
            direction_right=self.DIRECTION_BRAKE,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def get_last_response(self) -> Optional[dict]:
        return self._last_response
    
    def speed_to_percentage(self, speed: int) -> float:
        return (speed / 255.0) * 100.0
    
    def percentage_to_speed(self, percentage: float) -> int:
        if percentage < 0: percentage = 0
        elif percentage > 100: percentage = 100
        return int((percentage / 100.0) * 255)