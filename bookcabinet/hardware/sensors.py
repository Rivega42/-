"""
Датчики TCST2103 (оптопары)

ЛОГИКА БЕЗ ВНЕШНИХ РЕЗИСТОРОВ + ГИСТЕРЕЗИС + DEBOUNCE:
- Щель открыта → выход "плавает" (~30-70% HIGH)
- Щель закрыта → PUD_UP тянет к HIGH (100%)

Гистерезис: ≥98% = сработал, ≤95% = свободен
Debounce: 5 стабильных чтений для смены состояния
"""
from typing import Dict, Callable
from .gpio_manager import gpio
from ..config import GPIO_PINS, MOCK_MODE


# Параметры фильтрации для TCST2103 без резисторов
SENSOR_SAMPLES = 50
SENSOR_THRESHOLD_HIGH = 98  # ≥98% → сработал
SENSOR_THRESHOLD_LOW = 95   # ≤95% → свободен
SENSOR_DEBOUNCE = 5         # Нужно 5 стабильных чтений


class Sensors:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self._callbacks = {}
        
        self._pin_map = {
            'x_begin': 'SENSOR_X_BEGIN',
            'x_end': 'SENSOR_X_END',
            'y_begin': 'SENSOR_Y_BEGIN',
            'y_end': 'SENSOR_Y_END',
            'tray_begin': 'SENSOR_TRAY_BEGIN',
            'tray_end': 'SENSOR_TRAY_END',
        }
        
        # Состояние с гистерезисом и debounce
        self._state = {name: False for name in self._pin_map.keys()}
        self._pending = {name: None for name in self._pin_map.keys()}
        self._counter = {name: 0 for name in self._pin_map.keys()}
        
        # Инициализация датчиков с PUD_UP
        for pin_name in self._pin_map.values():
            pin = GPIO_PINS[pin_name]
            gpio.setup_input(pin, pull_up=True)
    
    def _read_percent(self, pin: int) -> int:
        """Читает пин несколько раз, возвращает % времени в HIGH"""
        if self.mock_mode:
            return 100 if gpio.read(pin) else 0
        
        readings = sum(gpio.read(pin) for _ in range(SENSOR_SAMPLES))
        return readings * 100 // SENSOR_SAMPLES
    
    def _update_state(self, sensor: str, percent: int) -> bool:
        """Обновляет состояние с гистерезисом и debounce"""
        # Определяем желаемое состояние
        if percent >= SENSOR_THRESHOLD_HIGH:
            desired = True
        elif percent <= SENSOR_THRESHOLD_LOW:
            desired = False
        else:
            desired = self._state[sensor]  # В зоне гистерезиса
        
        # Debounce
        if desired == self._pending[sensor]:
            self._counter[sensor] += 1
        else:
            self._pending[sensor] = desired
            self._counter[sensor] = 1
        
        if self._counter[sensor] >= SENSOR_DEBOUNCE and self._state[sensor] != desired:
            self._state[sensor] = desired
        
        return self._state[sensor]
    
    def read(self, sensor: str) -> int:
        """Читает состояние датчика (% времени в HIGH)"""
        pin_name = self._pin_map.get(sensor)
        if pin_name:
            return self._read_percent(GPIO_PINS[pin_name])
        return 0
    
    def is_triggered(self, sensor: str) -> bool:
        """Проверяет сработал ли датчик (с гистерезисом и debounce)"""
        percent = self.read(sensor)
        return self._update_state(sensor, percent)
    
    def read_all(self) -> Dict[str, int]:
        """Читает все датчики (% HIGH)"""
        return {name: self.read(name) for name in self._pin_map.keys()}
    
    def read_all_triggered(self) -> Dict[str, bool]:
        """Читает все датчики как bool (True = сработал)"""
        return {name: self.is_triggered(name) for name in self._pin_map.keys()}
    
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
        pin_name = self._pin_map.get(sensor)
        if pin_name:
            gpio.set_mock_sensor(GPIO_PINS[pin_name], value)
    
    def add_callback(self, sensor: str, callback: Callable):
        """Добавляет callback на изменение состояния датчика"""
        self._callbacks[sensor] = callback
    
    def get_status(self) -> Dict:
        """Возвращает полный статус всех датчиков для диагностики"""
        raw = self.read_all()
        triggered = self.read_all_triggered()
        return {
            'raw_percent': raw,
            'triggered': triggered,
            'threshold_high': SENSOR_THRESHOLD_HIGH,
            'threshold_low': SENSOR_THRESHOLD_LOW,
            'debounce': SENSOR_DEBOUNCE,
            'samples': SENSOR_SAMPLES,
            'tray_retracted': self.is_tray_retracted(),
            'tray_extended': self.is_tray_extended(),
            'at_home': self.is_at_home(),
        }


sensors = Sensors()
