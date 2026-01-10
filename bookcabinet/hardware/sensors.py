"""
Датчики TCST2103 (оптопары)

Используют встроенную подтяжку Raspberry Pi (резисторы 10K не нужны!)
Логика: LOW = датчик сработал (луч прерван), HIGH = свободен
"""
from typing import Dict, Callable, Optional
from .gpio_manager import gpio
from ..config import GPIO_PINS, MOCK_MODE, SENSOR_USE_PULLUP


class Sensors:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self._callbacks = {}
        
        sensor_pins = [
            'SENSOR_X_BEGIN', 'SENSOR_X_END',
            'SENSOR_Y_BEGIN', 'SENSOR_Y_END',
            'SENSOR_TRAY_BEGIN', 'SENSOR_TRAY_END',
        ]
        
        # Инициализация датчиков с подтяжкой из конфига
        for pin_name in sensor_pins:
            pin = GPIO_PINS[pin_name]
            gpio.setup_input(pin, pull_up=SENSOR_USE_PULLUP)
    
    def read(self, sensor: str) -> int:
        """Читает состояние датчика (0 = сработал, 1 = свободен)"""
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
    
    def is_triggered(self, sensor: str) -> bool:
        """Проверяет сработал ли датчик (луч прерван = LOW = True)"""
        return self.read(sensor) == 0
    
    def read_all(self) -> Dict[str, int]:
        """Читает все датчики"""
        return {
            'x_begin': self.read('x_begin'),
            'x_end': self.read('x_end'),
            'y_begin': self.read('y_begin'),
            'y_end': self.read('y_end'),
            'tray_begin': self.read('tray_begin'),
            'tray_end': self.read('tray_end'),
        }
    
    def read_all_triggered(self) -> Dict[str, bool]:
        """Читает все датчики как bool (True = сработал)"""
        return {
            'x_begin': self.is_triggered('x_begin'),
            'x_end': self.is_triggered('x_end'),
            'y_begin': self.is_triggered('y_begin'),
            'y_end': self.is_triggered('y_end'),
            'tray_begin': self.is_triggered('tray_begin'),
            'tray_end': self.is_triggered('tray_end'),
        }
    
    def is_tray_retracted(self) -> bool:
        """Платформа в заднем положении"""
        return self.is_triggered('tray_begin')
    
    def is_tray_extended(self) -> bool:
        """Платформа в переднем положении (выдвинута)"""
        return self.is_triggered('tray_end')
    
    def is_at_home(self) -> bool:
        """Каретка в домашней позиции (X=0, Y=0)"""
        return self.is_triggered('x_begin') and self.is_triggered('y_begin')
    
    def is_at_x_end(self) -> bool:
        """Каретка в правом положении X"""
        return self.is_triggered('x_end')
    
    def is_at_y_end(self) -> bool:
        """Каретка в верхнем положении Y"""
        return self.is_triggered('y_end')
    
    def set_mock(self, sensor: str, value: int):
        """Устанавливает значение датчика в mock режиме"""
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
        """Добавляет callback на изменение состояния датчика"""
        self._callbacks[sensor] = callback


sensors = Sensors()
