"""
Алгоритмы управления: INIT, TAKE, GIVE
"""
import asyncio
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from ..hardware.motors import motors
from ..hardware.servos import servos
from ..hardware.shutters import shutters
from ..hardware.sensors import sensors
from .corexy import corexy
from ..config import TIMEOUTS, MOCK_MODE


class Algorithms:
    def __init__(self):
        self.state = 'idle'
        self.current_operation = None
        self.progress_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
    
    def set_callbacks(self, progress: Callable = None, error: Callable = None):
        self.progress_callback = progress
        self.error_callback = error
    
    async def _emit_progress(self, step: int, total: int, message: str):
        if self.progress_callback:
            await self.progress_callback({
                'step': step,
                'total': total,
                'message': message,
                'operation': self.current_operation,
            })
    
    async def _emit_error(self, code: int, message: str):
        if self.error_callback:
            await self.error_callback({
                'code': code,
                'message': message,
                'operation': self.current_operation,
            })
    
    async def init_home(self) -> bool:
        self.current_operation = 'INIT'
        self.state = 'homing'
        
        try:
            await self._emit_progress(1, 4, 'Проверка платформы')
            
            if not sensors.is_tray_retracted():
                await self._emit_progress(2, 4, 'Втягивание платформы')
                await motors.retract_tray()
            
            await self._emit_progress(3, 4, 'Поиск начальной позиции X')
            await motors.move_xy(0, motors.position['y'])
            
            await self._emit_progress(4, 4, 'Поиск начальной позиции Y')
            await motors.move_xy(0, 0)
            
            if MOCK_MODE:
                sensors.set_mock('x_begin', 1)
                sensors.set_mock('y_begin', 1)
                sensors.set_mock('tray_begin', 1)
            
            self.state = 'idle'
            return True
            
        except Exception as e:
            await self._emit_error(1, f'Ошибка инициализации: {e}')
            self.state = 'error'
            return False
    
    async def take_shelf(self, row: str, x: int, y: int) -> bool:
        self.current_operation = 'TAKE'
        self.state = 'busy'
        total_steps = 13
        
        try:
            await self._emit_progress(1, total_steps, 'Проверка платформы')
            if not sensors.is_tray_retracted():
                await motors.retract_tray()
            
            await self._emit_progress(2, total_steps, f'Перемещение к ячейке ({row}, {x}, {y})')
            target_x, target_y = corexy.cell_to_steps(row, x, y)
            await motors.move_xy(target_x, target_y)
            
            await self._emit_progress(3, total_steps, 'Выдвижение платформы (1-й этап)')
            await motors.extend_tray()
            
            await self._emit_progress(4, total_steps, 'Закрытие замка')
            lock = 'lock1' if row == 'FRONT' else 'lock2'
            await servos.close_lock(lock)
            
            await self._emit_progress(5, total_steps, 'Втягивание')
            await motors.retract_tray()
            
            await self._emit_progress(6, total_steps, 'Открытие замка')
            await servos.open_lock(lock)
            
            await self._emit_progress(7, total_steps, 'Выдвижение платформы (2-й этап)')
            await motors.extend_tray()
            
            await self._emit_progress(8, total_steps, 'Закрытие замка')
            await servos.close_lock(lock)
            
            await self._emit_progress(9, total_steps, 'Полное втягивание')
            await motors.retract_tray()
            
            await self._emit_progress(10, total_steps, 'Перемещение к окну')
            window_x, window_y = corexy.window_position()
            await motors.move_xy(window_x, window_y)
            
            await self._emit_progress(11, total_steps, 'Открытие внутренней шторки')
            await shutters.open_shutter('inner')
            
            await self._emit_progress(12, total_steps, 'Выдвижение в окно')
            await motors.extend_tray()
            
            await self._emit_progress(13, total_steps, 'Открытие внешней шторки')
            await shutters.open_shutter('outer')
            
            self.state = 'waiting_user'
            return True
            
        except Exception as e:
            await self._emit_error(2, f'Ошибка TAKE: {e}')
            self.state = 'error'
            return False
    
    async def give_shelf(self, row: str, x: int, y: int) -> bool:
        self.current_operation = 'GIVE'
        self.state = 'busy'
        total_steps = 10
        
        try:
            await self._emit_progress(1, total_steps, 'Закрытие внешней шторки')
            await shutters.close_shutter('outer')
            
            await self._emit_progress(2, total_steps, 'Втягивание платформы')
            await motors.retract_tray()
            
            await self._emit_progress(3, total_steps, 'Закрытие внутренней шторки')
            await shutters.close_shutter('inner')
            
            await self._emit_progress(4, total_steps, f'Перемещение к ячейке ({row}, {x}, {y})')
            target_x, target_y = corexy.cell_to_steps(row, x, y)
            await motors.move_xy(target_x, target_y)
            
            await self._emit_progress(5, total_steps, 'Выдвижение платформы')
            await motors.extend_tray()
            
            await self._emit_progress(6, total_steps, 'Открытие замка')
            lock = 'lock1' if row == 'FRONT' else 'lock2'
            await servos.open_lock(lock)
            
            await self._emit_progress(7, total_steps, 'Втягивание')
            await motors.retract_tray()
            
            await self._emit_progress(8, total_steps, 'Закрытие замка')
            await servos.close_lock(lock)
            
            await self._emit_progress(9, total_steps, 'Выдвижение (вставка полки)')
            await motors.extend_tray()
            
            await self._emit_progress(10, total_steps, 'Полное втягивание')
            await motors.retract_tray()
            
            self.state = 'idle'
            return True
            
        except Exception as e:
            await self._emit_error(3, f'Ошибка GIVE: {e}')
            self.state = 'error'
            return False
    
    async def wait_for_user(self, timeout_ms: int = None) -> bool:
        timeout = timeout_ms or TIMEOUTS['user_wait']
        await asyncio.sleep(timeout / 1000)
        return True
    
    def stop(self):
        motors.stop()
        self.state = 'stopped'
    
    def get_state(self) -> Dict[str, Any]:
        return {
            'state': self.state,
            'current_operation': self.current_operation,
            'position': motors.get_position(),
            'sensors': sensors.read_all(),
            'servos': servos.get_all_states(),
            'shutters': shutters.get_all_states(),
        }


algorithms = Algorithms()
