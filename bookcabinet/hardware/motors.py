"""
Управление моторами CoreXY и платформой
"""
import asyncio
from typing import Tuple
from .gpio_manager import gpio
from ..config import GPIO_PINS, MOTOR_SPEEDS, MOCK_MODE, TIMEOUTS


class Motors:
    def __init__(self):
        self.position = {'x': 0, 'y': 0, 'tray': 0}
        self.is_moving = False
        self.mock_mode = MOCK_MODE
        
        gpio.setup_output(GPIO_PINS['MOTOR_A_STEP'])
        gpio.setup_output(GPIO_PINS['MOTOR_A_DIR'])
        gpio.setup_output(GPIO_PINS['MOTOR_B_STEP'])
        gpio.setup_output(GPIO_PINS['MOTOR_B_DIR'])
        gpio.setup_output(GPIO_PINS['TRAY_STEP'])
        gpio.setup_output(GPIO_PINS['TRAY_DIR'])
    
    async def move_xy(self, target_x: int, target_y: int) -> bool:
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            dx = target_x - self.position['x']
            dy = target_y - self.position['y']
            
            steps_a = dx + dy
            steps_b = -dx + dy
            
            dir_a = 1 if steps_a > 0 else 0
            dir_b = 1 if steps_b > 0 else 0
            
            gpio.write(GPIO_PINS['MOTOR_A_DIR'], dir_a)
            gpio.write(GPIO_PINS['MOTOR_B_DIR'], dir_b)
            
            if self.mock_mode:
                await asyncio.sleep(TIMEOUTS['move'] / 1000)
            else:
                max_steps = max(abs(steps_a), abs(steps_b))
                delay_us = int(1_000_000 / MOTOR_SPEEDS['xy'])
                
                for i in range(max_steps):
                    if i < abs(steps_a):
                        gpio.write(GPIO_PINS['MOTOR_A_STEP'], 1)
                    if i < abs(steps_b):
                        gpio.write(GPIO_PINS['MOTOR_B_STEP'], 1)
                    await asyncio.sleep(delay_us / 1_000_000)
                    gpio.write(GPIO_PINS['MOTOR_A_STEP'], 0)
                    gpio.write(GPIO_PINS['MOTOR_B_STEP'], 0)
                    await asyncio.sleep(delay_us / 1_000_000)
            
            self.position['x'] = target_x
            self.position['y'] = target_y
            return True
            
        finally:
            self.is_moving = False
    
    async def move_tray(self, direction: str, steps: int = None) -> bool:
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            is_extend = direction in ('extend', 'out', '+')
            gpio.write(GPIO_PINS['TRAY_DIR'], 1 if is_extend else 0)
            
            if self.mock_mode:
                timeout = TIMEOUTS['tray_extend'] if is_extend else TIMEOUTS['tray_retract']
                await asyncio.sleep(timeout / 1000)
            else:
                steps = steps or 3000
                delay_us = int(1_000_000 / MOTOR_SPEEDS['tray'])
                for _ in range(steps):
                    gpio.write(GPIO_PINS['TRAY_STEP'], 1)
                    await asyncio.sleep(delay_us / 1_000_000)
                    gpio.write(GPIO_PINS['TRAY_STEP'], 0)
                    await asyncio.sleep(delay_us / 1_000_000)
            
            self.position['tray'] = 1 if is_extend else 0
            return True
            
        finally:
            self.is_moving = False
    
    async def extend_tray(self, steps: int = None) -> bool:
        return await self.move_tray('extend', steps)
    
    async def retract_tray(self, steps: int = None) -> bool:
        return await self.move_tray('retract', steps)
    
    def get_position(self) -> dict:
        return self.position.copy()
    
    def stop(self):
        self.is_moving = False
        gpio.write(GPIO_PINS['MOTOR_A_STEP'], 0)
        gpio.write(GPIO_PINS['MOTOR_B_STEP'], 0)
        gpio.write(GPIO_PINS['TRAY_STEP'], 0)


motors = Motors()
