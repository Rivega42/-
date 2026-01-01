"""
Watchdog - мониторинг состояния системы
"""
import asyncio
import os
import socket
from typing import Dict, Optional, Callable
from datetime import datetime
from ..config import MOCK_MODE
from ..database import db


class WatchdogService:
    def __init__(self):
        self._running = False
        self._last_heartbeat = datetime.now()
        self._check_interval = 30
        self._error_callback: Optional[Callable] = None
        self._health_status: Dict = {
            'motors': True,
            'sensors': True,
            'rfid_card': True,
            'rfid_book': True,
            'database': True,
            'websocket': True,
        }
        self._consecutive_failures: Dict[str, int] = {}
        self._max_failures = 3
    
    def set_error_callback(self, callback: Callable):
        self._error_callback = callback
    
    async def start(self, interval: int = 30):
        self._running = True
        self._check_interval = interval
        
        db.add_system_log('INFO', 'Watchdog запущен', 'watchdog')
        
        while self._running:
            try:
                await self._check_health()
                self._last_heartbeat = datetime.now()
                
                if not MOCK_MODE:
                    self._notify_systemd()
                
            except Exception as e:
                db.add_system_log('ERROR', f'Ошибка watchdog: {e}', 'watchdog')
            
            await asyncio.sleep(self._check_interval)
    
    def stop(self):
        self._running = False
        db.add_system_log('INFO', 'Watchdog остановлен', 'watchdog')
    
    async def _check_health(self):
        await self._check_motors()
        await self._check_sensors()
        await self._check_rfid()
        await self._check_database()
        await self._check_websocket()
    
    async def _check_motors(self):
        try:
            from ..hardware.motors import motors
            
            pos = motors.get_position()
            if pos is None:
                self._report_failure('motors', 'Не удалось получить позицию')
            else:
                self._report_success('motors')
        except Exception as e:
            self._report_failure('motors', str(e))
    
    async def _check_sensors(self):
        try:
            from ..hardware.sensors import sensors
            
            data = sensors.read_all()
            if data is None:
                self._report_failure('sensors', 'Не удалось прочитать датчики')
            else:
                self._report_success('sensors')
        except Exception as e:
            self._report_failure('sensors', str(e))
    
    async def _check_rfid(self):
        try:
            from ..rfid.card_reader import card_reader
            from ..rfid.book_reader import book_reader
            
            if card_reader.mock_mode or card_reader.reader is not None:
                self._report_success('rfid_card')
            else:
                self._report_failure('rfid_card', 'Ридер карт не подключён')
            
            if book_reader.mock_mode or book_reader.serial is not None:
                self._report_success('rfid_book')
            else:
                self._report_failure('rfid_book', 'Ридер книг не подключён')
        except Exception as e:
            self._report_failure('rfid_card', str(e))
            self._report_failure('rfid_book', str(e))
    
    async def _check_database(self):
        try:
            stats = db.get_statistics()
            if stats is not None:
                self._report_success('database')
            else:
                self._report_failure('database', 'Ошибка доступа к БД')
        except Exception as e:
            self._report_failure('database', str(e))
    
    async def _check_websocket(self):
        try:
            from ..server.websocket_handler import ws_handler
            
            client_count = len(ws_handler.clients)
            if client_count >= 0:
                self._report_success('websocket')
        except Exception as e:
            self._report_failure('websocket', str(e))
    
    def _report_failure(self, component: str, message: str):
        self._consecutive_failures[component] = self._consecutive_failures.get(component, 0) + 1
        
        if self._consecutive_failures[component] >= self._max_failures:
            if self._health_status.get(component, True):
                self._health_status[component] = False
                error_msg = f'Компонент {component} недоступен: {message}'
                db.add_system_log('ERROR', error_msg, 'watchdog')
                
                if self._error_callback:
                    asyncio.create_task(self._notify_error(component, message))
    
    def _report_success(self, component: str):
        was_failed = not self._health_status.get(component, True)
        self._health_status[component] = True
        self._consecutive_failures[component] = 0
        
        if was_failed:
            db.add_system_log('INFO', f'Компонент {component} восстановлен', 'watchdog')
    
    async def _notify_error(self, component: str, message: str):
        if self._error_callback:
            try:
                await self._error_callback(component, message)
            except:
                pass
    
    def _notify_systemd(self):
        try:
            notify_socket = os.environ.get('NOTIFY_SOCKET')
            if notify_socket:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                sock.connect(notify_socket)
                sock.sendall(b'WATCHDOG=1')
                sock.close()
        except:
            pass
    
    def get_health_status(self) -> Dict:
        all_healthy = all(self._health_status.values())
        return {
            'healthy': all_healthy,
            'components': self._health_status.copy(),
            'last_check': self._last_heartbeat.isoformat(),
            'uptime_seconds': (datetime.now() - self._last_heartbeat).total_seconds() if self._running else 0,
        }
    
    def is_healthy(self) -> bool:
        return all(self._health_status.values())
    
    def heartbeat(self):
        self._last_heartbeat = datetime.now()


watchdog = WatchdogService()
