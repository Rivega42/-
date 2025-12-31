"""
GPIO Manager - pigpio или mock
"""
import asyncio
from typing import Callable, Optional
from ..config import MOCK_MODE, GPIO_PINS


class GPIOManager:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self.pi = None
        self._callbacks = {}
        self._pin_states = {pin: 0 for pin in GPIO_PINS.values()}
        
        if not self.mock_mode:
            try:
                import pigpio
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    print("WARNING: pigpio not connected, switching to mock mode")
                    self.mock_mode = True
            except ImportError:
                print("WARNING: pigpio not installed, switching to mock mode")
                self.mock_mode = True
    
    def setup_output(self, pin: int):
        if not self.mock_mode and self.pi:
            self.pi.set_mode(pin, 1)
        self._pin_states[pin] = 0
    
    def setup_input(self, pin: int, pull_up: bool = True):
        if not self.mock_mode and self.pi:
            import pigpio
            pud = pigpio.PUD_UP if pull_up else pigpio.PUD_DOWN
            self.pi.set_mode(pin, 0)
            self.pi.set_pull_up_down(pin, pud)
        self._pin_states[pin] = 1 if pull_up else 0
    
    def write(self, pin: int, value: int):
        if not self.mock_mode and self.pi:
            self.pi.write(pin, value)
        self._pin_states[pin] = value
    
    def read(self, pin: int) -> int:
        if not self.mock_mode and self.pi:
            return self.pi.read(pin)
        return self._pin_states.get(pin, 0)
    
    def set_servo_pulsewidth(self, pin: int, pulsewidth: int):
        if not self.mock_mode and self.pi:
            self.pi.set_servo_pulsewidth(pin, pulsewidth)
    
    def set_pwm_dutycycle(self, pin: int, dutycycle: int):
        if not self.mock_mode and self.pi:
            self.pi.set_PWM_dutycycle(pin, dutycycle)
    
    def set_pwm_frequency(self, pin: int, frequency: int):
        if not self.mock_mode and self.pi:
            self.pi.set_PWM_frequency(pin, frequency)
    
    async def pulse(self, pin: int, count: int, delay_us: int = 250):
        delay_s = delay_us / 1_000_000
        for _ in range(count):
            self.write(pin, 1)
            await asyncio.sleep(delay_s)
            self.write(pin, 0)
            await asyncio.sleep(delay_s)
    
    def add_callback(self, pin: int, edge: int, callback: Callable):
        if not self.mock_mode and self.pi:
            self.pi.callback(pin, edge, callback)
        self._callbacks[pin] = callback
    
    def set_mock_sensor(self, pin: int, value: int):
        if self.mock_mode:
            self._pin_states[pin] = value
            if pin in self._callbacks:
                self._callbacks[pin](pin, value, 0)
    
    def cleanup(self):
        if not self.mock_mode and self.pi:
            self.pi.stop()


gpio = GPIOManager()
