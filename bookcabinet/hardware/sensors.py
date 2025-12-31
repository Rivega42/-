"""
Датчики TCST2103
"""
from typing import Dict, Callable, Optional
from .gpio_manager import gpio
from ..config import GPIO_PINS, MOCK_MODE


class Sensors:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self._callbacks = {}
        
        sensor_pins = [
            'SENSOR_X_BEGIN', 'SENSOR_X_END',
            'SENSOR_Y_BEGIN', 'SENSOR_Y_END',
            'SENSOR_TRAY_BEGIN', 'SENSOR_TRAY_END',
        ]
        
        for pin_name in sensor_pins:
            pin = GPIO_PINS[pin_name]
            gpio.setup_input(pin, pull_up=True)
    
    def read(self, sensor: str) -> int:
        pin_map = {
            'x_begin': 'SENSOR_X_BEGIN',
            'x_end': 'SENSOR_X_END',
            'y_begin': 'SENSOR_Y_BEGIN',
            'y_end': 'SENSOR_Y_END',
            'tray_begin': 'SENSOR_TRAY_BEGIN',
            'tray_end': 'SENSOR_TRAY_END',
        }
        pin_name = pin_map.get(sensor)
        if pin_name:
            return gpio.read(GPIO_PINS[pin_name])
        return 0
    
    def read_all(self) -> Dict[str, int]:
        return {
            'x_begin': self.read('x_begin'),
            'x_end': self.read('x_end'),
            'y_begin': self.read('y_begin'),
            'y_end': self.read('y_end'),
            'tray_begin': self.read('tray_begin'),
            'tray_end': self.read('tray_end'),
        }
    
    def is_tray_retracted(self) -> bool:
        return self.read('tray_begin') == 1
    
    def is_tray_extended(self) -> bool:
        return self.read('tray_end') == 1
    
    def is_at_home(self) -> bool:
        return self.read('x_begin') == 1 and self.read('y_begin') == 1
    
    def set_mock(self, sensor: str, value: int):
        pin_map = {
            'x_begin': 'SENSOR_X_BEGIN',
            'x_end': 'SENSOR_X_END',
            'y_begin': 'SENSOR_Y_BEGIN',
            'y_end': 'SENSOR_Y_END',
            'tray_begin': 'SENSOR_TRAY_BEGIN',
            'tray_end': 'SENSOR_TRAY_END',
        }
        pin_name = pin_map.get(sensor)
        if pin_name:
            gpio.set_mock_sensor(GPIO_PINS[pin_name], value)
    
    def add_callback(self, sensor: str, callback: Callable):
        self._callbacks[sensor] = callback


sensors = Sensors()
