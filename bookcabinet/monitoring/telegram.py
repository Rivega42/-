"""
Telegram уведомления - полная реализация
"""
import asyncio
from typing import Optional
from ..config import TELEGRAM
from ..database import db


class TelegramNotifier:
    def __init__(self):
        self.enabled = TELEGRAM['enabled']
        self.bot_token = TELEGRAM['bot_token']
        self.chat_id = TELEGRAM['chat_id']
        self._session = None
    
    def configure(self, bot_token: str, chat_id: str, enabled: bool = True):
        """Настроить Telegram"""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
    
    async def send(self, message: str, level: str = 'info') -> bool:
        """Отправить сообщение в Telegram"""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False
        
        emoji = {
            'info': 'ℹ️',
            'error': '🔴',
            'success': '✅',
            'warning': '⚠️',
            'critical': '🆘',
        }.get(level, 'ℹ️')
        
        text = f"{emoji} *BookCabinet*\n{message}"
        
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    'chat_id': self.chat_id,
                    'text': text,
                    'parse_mode': 'Markdown'
                }, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    result = await response.json()
                    success = result.get('ok', False)
                    
                    if success:
                        db.add_system_log('INFO', f'Telegram: отправлено "{message[:50]}..."', 'telegram')
                    else:
                        db.add_system_log('ERROR', f'Telegram ошибка: {result}', 'telegram')
                    
                    return success
                    
        except asyncio.TimeoutError:
            db.add_system_log('ERROR', 'Telegram: таймаут соединения', 'telegram')
            return False
        except ImportError:
            db.add_system_log('ERROR', 'Telegram: aiohttp не установлен', 'telegram')
            return False
        except Exception as e:
            db.add_system_log('ERROR', f'Telegram ошибка: {e}', 'telegram')
            return False
    
    async def notify_startup(self):
        """Уведомление о запуске системы"""
        await self.send("🚀 Система запущена и готова к работе", "success")
    
    async def notify_shutdown(self):
        """Уведомление об остановке"""
        await self.send("🛑 Система остановлена", "warning")
    
    async def notify_error(self, error: str, component: str = None):
        """Уведомление об ошибке"""
        msg = f"Ошибка"
        if component:
            msg += f" [{component}]"
        msg += f": {error}"
        await self.send(msg, "error")
    
    async def notify_critical(self, message: str):
        """Критическое уведомление"""
        await self.send(f"⚠️ КРИТИЧЕСКАЯ ОШИБКА: {message}", "critical")
    
    async def notify_irbis_status(self, connected: bool):
        """Уведомление о статусе ИРБИС"""
        if connected:
            await self.send("✅ Связь с ИРБИС восстановлена", "success")
        else:
            await self.send("❌ Потеряна связь с ИРБИС. Работа в автономном режиме.", "error")
    
    async def notify_low_space(self, available_cells: int, total_cells: int):
        """Уведомление о заполненности шкафа"""
        percent = (1 - available_cells / total_cells) * 100
        if percent > 90:
            await self.send(f"📦 Шкаф почти заполнен: {percent:.0f}% ({available_cells} свободных ячеек)", "warning")
    
    async def notify_extraction_needed(self, count: int):
        """Уведомление о необходимости изъятия книг"""
        if count > 0:
            await self.send(f"📚 Требуется изъятие: {count} книг ожидают в ячейках", "info")
    
    async def notify_maintenance(self, issue: str):
        """Уведомление о необходимости обслуживания"""
        await self.send(f"🔧 Требуется обслуживание: {issue}", "warning")


telegram = TelegramNotifier()
