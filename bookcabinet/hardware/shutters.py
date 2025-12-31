"""
Управление шторками
"""
import asyncio
from .gpio_manager import gpio
from ..config import GPIO_PINS, MOCK_MODE


class Shutters:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self.states = {
            'outer': 'closed',
            'inner': 'closed',
        }
        
        gpio.setup_output(GPIO_PINS['SHUTTER_OUTER'])
        gpio.setup_output(GPIO_PINS['SHUTTER_INNER'])
    
    async def open_shutter(self, shutter: str = 'outer'):
        pin = GPIO_PINS['SHUTTER_OUTER'] if shutter == 'outer' else GPIO_PINS['SHUTTER_INNER']
        gpio.write(pin, 1)
        await asyncio.sleep(0.5)
        self.states[shutter] = 'open'
    
    async def close_shutter(self, shutter: str = 'outer'):
        pin = GPIO_PINS['SHUTTER_OUTER'] if shutter == 'outer' else GPIO_PINS['SHUTTER_INNER']
        gpio.write(pin, 0)
        await asyncio.sleep(0.5)
        self.states[shutter] = 'closed'
    
    async def open_window(self):
        await self.open_shutter('inner')
        await self.open_shutter('outer')
    
    async def close_window(self):
        await self.close_shutter('outer')
        await self.close_shutter('inner')
    
    def get_state(self, shutter: str = 'outer') -> str:
        return self.states.get(shutter, 'unknown')
    
    def get_all_states(self) -> dict:
        return self.states.copy()


shutters = Shutters()
