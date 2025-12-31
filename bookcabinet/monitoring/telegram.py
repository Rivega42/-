"""
Telegram уведомления
"""
import asyncio
from typing import Optional
from ..config import TELEGRAM


class TelegramNotifier:
    def __init__(self):
        self.enabled = TELEGRAM['enabled']
        self.bot_token = TELEGRAM['bot_token']
        self.chat_id = TELEGRAM['chat_id']
    
    async def send(self, message: str, level: str = 'info') -> bool:
        if not self.enabled:
            return False
        
        emoji = {
            'info': 'ℹ️',
            'error': '🔴',
            'success': '✅',
            'warning': '⚠️'
        }.get(level, 'ℹ️')
        
        text = f"{emoji} BookCabinet\n{message}"
        
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            async with aiohttp.ClientSession() as session:
                await session.post(url, json={
                    'chat_id': self.chat_id,
                    'text': text
                })
            return True
        except:
            return False
    
    async def notify_startup(self):
        await self.send("Система запущена", "success")
    
    async def notify_error(self, error: str):
        await self.send(f"Ошибка: {error}", "error")
    
    async def notify_irbis_status(self, connected: bool):
        if connected:
            await self.send("Связь с ИРБИС восстановлена", "success")
        else:
            await self.send("ИРБИС недоступен", "error")


telegram = TelegramNotifier()
