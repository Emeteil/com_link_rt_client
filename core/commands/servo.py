from .base import BaseCommand
import threading
import struct

from ..protocol import ServiceBits

class ServoCommand(BaseCommand):
    MOVE_IMMEDIATE = 0x01 # Резкий поворот (высший приоритет)
    MOVE_SMOOTH_LOW = 0x02 # Плавный поворот (низкий приоритет)
    MOVE_SMOOTH_HIGH = 0x03 # Плавный поворот (высокий приоритет)
    
    MODE_ABSOLUTE = 0x01 # Абсолютная позиция
    MODE_RELATIVE = 0x02 # Относительная позиция
    MODE_CALIBRATION = 0x03 # Калибровка
    
    def __init__(self, connection):
        self.PACKET_TYPE_REQUEST = 0x09
        self.PACKET_TYPE_RESPONSE = 0x0A
        super().__init__(connection, self.PACKET_TYPE_REQUEST, self.PACKET_TYPE_RESPONSE)
        
        self.connection.register_handler(self.PACKET_TYPE_RESPONSE, self._handle_response)
        
    def _handle_response(self, packet: dict):
        pass
    
    def _create_command_data(self, channel: int, move_type: int, target_angle: int, step_delay: int = 0, mode: int = MODE_ABSOLUTE) -> bytes:
        return struct.pack('<BBHHB', channel, move_type, target_angle, step_delay, mode)
    
    def move_immediate(self, channel: int, angle: int, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=self.MOVE_IMMEDIATE,
            target_angle=angle,
            step_delay=0,
            mode=self.MODE_ABSOLUTE,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def move_smooth_low(self, channel: int, angle: int, step_delay_ms: int = 50, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=self.MOVE_SMOOTH_LOW,
            target_angle=angle,
            step_delay=step_delay_ms,
            mode=self.MODE_ABSOLUTE,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def move_smooth_high(self, channel: int, angle: int, step_delay_ms: int = 50, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=self.MOVE_SMOOTH_HIGH,
            target_angle=angle,
            step_delay=step_delay_ms,
            mode=self.MODE_ABSOLUTE,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def move_relative(self, channel: int, delta_angle: int, move_type: int = MOVE_IMMEDIATE, step_delay_ms: int = 50, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=move_type,
            target_angle=delta_angle,
            step_delay=step_delay_ms,
            mode=self.MODE_RELATIVE,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def execute(self, channel: int, move_type: int, target_angle: int, step_delay_ms: int = 0, mode: int = MODE_ABSOLUTE, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=move_type,
            target_angle=target_angle,
            step_delay=step_delay_ms,
            mode=mode,
            wait_response=wait_response,
            timeout=timeout
        )
    
    def _send_command(self, channel: int, move_type: int, target_angle: int, step_delay: int, mode: int, wait_response: bool, timeout: float) -> bool:
        if channel < 0 or channel > 15:
            raise ValueError("Значение канала должно быть в диапазоне от 0 до 15.")
        
        if target_angle < 0 or target_angle > 180:
            raise ValueError("Целевой угол должен находиться в диапазоне от 0 до 180 градусов.")
        
        if move_type not in [self.MOVE_IMMEDIATE, self.MOVE_SMOOTH_LOW, self.MOVE_SMOOTH_HIGH]:
            raise ValueError("Недопустимый тип хода.")
        
        if mode not in [self.MODE_ABSOLUTE, self.MODE_RELATIVE, self.MODE_CALIBRATION]:
            raise ValueError("Недопустимый режим.")
        
        if step_delay < 0 or step_delay > 65535:
            raise ValueError("Задержка шага должна быть в диапазоне от 0 до 65535 мс.")
        
        command_data = self._create_command_data(
            channel=channel,
            move_type=move_type,
            target_angle=target_angle,
            step_delay=step_delay,
            mode=mode
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
    
    def sweep(self, channel: int, start_angle: int, end_angle: int, step_delay_ms: int = 50, move_type: int = MOVE_SMOOTH_LOW, wait_each: bool = False, timeout: float = 2.0) -> bool:
        if start_angle < 0 or start_angle > 180 or end_angle < 0 or end_angle > 180:
            raise ValueError("Углы должны быть в диапазоне от 0 до 180 градусов.")
        
        current_angle = start_angle
        step = 1 if end_angle > start_angle else -1
        
        while current_angle != end_angle:
            success = self._send_command(
                channel=channel,
                move_type=move_type,
                target_angle=current_angle,
                step_delay=step_delay_ms,
                mode=self.MODE_ABSOLUTE,
                wait_response=wait_each,
                timeout=timeout if wait_each else 0
            )
            
            if wait_each and not success:
                return False
            
            current_angle += step
            if (step > 0 and current_angle > end_angle) or (step < 0 and current_angle < end_angle):
                current_angle = end_angle
        
        return True
    
    def calibrate(self, channel: int, calibrate_angle: int = 90, wait_response: bool = True, timeout: float = 2.0) -> bool:
        return self._send_command(
            channel=channel,
            move_type=self.MOVE_IMMEDIATE,
            target_angle=calibrate_angle,
            step_delay=0,
            mode=self.MODE_CALIBRATION,
            wait_response=wait_response,
            timeout=timeout
        )