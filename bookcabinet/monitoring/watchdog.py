"""
Watchdog для автовосстановления
"""
import asyncio
import time
import os


class Watchdog:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.last_heartbeat = time.time()
        self._running = False
    
    def heartbeat(self):
        self.last_heartbeat = time.time()
    
    async def start(self):
        self._running = True
        while self._running:
            if time.time() - self.last_heartbeat > self.timeout:
                await self._restart_service()
            await asyncio.sleep(10)
    
    def stop(self):
        self._running = False
    
    async def _restart_service(self):
        print("Watchdog: перезапуск сервиса...")
        os.system("sudo systemctl restart bookcabinet")


watchdog = Watchdog()
