"""
LibraryService - Унифицированный сервис для работы с ИРБИС64

Предоставляет единый интерфейс для:
- Аутентификации пользователей
- Выдачи и возврата книг
- Проверки бронирований
- Загрузки и изъятия книг

Автоматически переключается между mock и реальным ИРБИС клиентом.
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

from ..config import IRBIS
from .client import IrbisClient, IrbisConfig
from .mock import mock_irbis
from ..utils.irbis_helpers import (
    normalize_rfid, format_book_brief, find_exemplar_by_rfid,
    get_field_value, get_field_values, get_active_loans, parse_subfields
)


class LibraryService:
    """
    Унифицированный сервис библиотечных операций
    
    Автоматически использует mock или реальный ИРБИС в зависимости от конфигурации.
    """
    
    def __init__(self):
        self.use_mock = IRBIS.get('mock', True)
        
        if self.use_mock:
            self.irbis = mock_irbis
        else:
            self.irbis = IrbisClient(IrbisConfig(
                host=IRBIS.get('host', '127.0.0.1'),
                port=IRBIS.get('port', 6666),
                username=IRBIS.get('username', 'MASTER'),
                password=IRBIS.get('password', 'MASTERKEY'),
                database=IRBIS.get('database', 'IBIS'),
                readers_database=IRBIS.get('readers_database', 'RDR'),
                loan_days=IRBIS.get('loan_days', 30),
                location_code=IRBIS.get('location_code', '09'),
            ))
        
        self.current_reader_mfn: Optional[int] = None
        self.current_reader_info: Optional[Dict] = None
    
    async def connect(self) -> bool:
        """Подключение к ИРБИС"""
        return await self.irbis.connect()
    
    async def disconnect(self):
        """Отключение от ИРБИС"""
        await self.irbis.disconnect()
    
    async def check_connection(self) -> bool:
        """Проверка подключения"""
        return await self.irbis.check_connection()
    
    async def authenticate(self, card_uid: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Аутентификация пользователя по карте
        
        Args:
            card_uid: UID карты (HEX)
        
        Returns:
            (success, message, user_info)
        """
        self.current_reader_mfn = None
        self.current_reader_info = None
        
        if not card_uid:
            return False, "Пустой UID карты", None
        
        user = await self.irbis.get_user(card_uid)
        
        if not user:
            return False, "Карта не зарегистрирована", None
        
        self.current_reader_mfn = user.get("mfn")
        self.current_reader_info = user
        
        name = user.get("name", "Читатель")
        return True, f"Добро пожаловать, {name}!", user
    
    def logout(self):
        """Выход из сессии"""
        self.current_reader_mfn = None
        self.current_reader_info = None
    
    def get_current_user(self) -> Optional[Dict]:
        """Получить текущего пользователя"""
        return self.current_reader_info
    
    def has_role(self, *roles: str) -> bool:
        """Проверить роль текущего пользователя"""
        if not self.current_reader_info:
            return False
        return self.current_reader_info.get("role") in roles
    
    async def get_reservations(self, user_rfid: Optional[str] = None) -> List[Dict]:
        """
        Получить список забронированных/выданных книг
        
        Args:
            user_rfid: UID карты пользователя (если не указан, используется текущий)
        """
        if user_rfid is None:
            if self.current_reader_info:
                user_rfid = self.current_reader_info.get("rfid", "")
            else:
                return []
        
        return await self.irbis.get_reservations(user_rfid or "")
    
    async def get_book_info(self, rfid: str) -> Optional[Dict]:
        """
        Получить информацию о книге по RFID
        """
        return await self.irbis.get_book(rfid)
    
    async def issue_book(self, book_rfid: str, user_rfid: Optional[str] = None) -> Tuple[bool, str]:
        """
        Выдача книги
        
        Args:
            book_rfid: RFID метка книги
            user_rfid: UID карты читателя (если не указан, используется текущий)
        """
        if user_rfid is None:
            if self.current_reader_info:
                user_rfid = self.current_reader_info.get("rfid", "")
            else:
                return False, "Требуется авторизация"
        
        if hasattr(self.irbis, 'issue_book'):
            return await self.irbis.issue_book(book_rfid, user_rfid or "")
        else:
            success = await self.irbis.register_issue(book_rfid, user_rfid or "")
            if success:
                return True, "Книга выдана"
            return False, "Ошибка выдачи"
    
    async def return_book(self, book_rfid: str) -> Tuple[bool, str]:
        """
        Возврат книги
        
        Args:
            book_rfid: RFID метка книги
        """
        if hasattr(self.irbis, 'return_book'):
            return await self.irbis.return_book(book_rfid)
        else:
            success = await self.irbis.register_return(book_rfid)
            if success:
                return True, "Книга возвращена"
            return False, "Ошибка возврата"
    
    async def verify_book_for_loading(self, rfid: str) -> Dict:
        """
        Проверка книги перед загрузкой в шкаф
        
        Возвращает:
        {
            "rfid": str,
            "status": "available" | "issued" | "not_found" | "error",
            "title": str,
            "warning": str | None,
            "can_load": bool
        }
        """
        book = await self.irbis.get_book(rfid)
        
        if not book:
            return {
                "rfid": rfid,
                "status": "not_found",
                "title": "",
                "warning": "Книга не найдена в каталоге",
                "can_load": False,
            }
        
        result = {
            "rfid": rfid,
            "status": book.get("status", "available"),
            "title": book.get("title", ""),
            "warning": None,
            "can_load": True,
        }
        
        if book.get("status") == "issued":
            result["warning"] = "Книга числится выданной! Требуется оформить возврат."
            result["can_load"] = True
        
        return result
    
    async def verify_book_for_extraction(self, rfid: str) -> Dict:
        """
        Проверка книги перед изъятием из шкафа
        
        Возвращает:
        {
            "rfid": str,
            "status": "ok" | "issued" | "not_found",
            "title": str,
            "action": str | None
        }
        """
        book = await self.irbis.get_book(rfid)
        
        if not book:
            return {
                "rfid": rfid,
                "status": "not_found",
                "title": "",
                "action": "Требуется ручная проверка",
            }
        
        result = {
            "rfid": rfid,
            "status": "ok",
            "title": book.get("title", ""),
            "action": None,
        }
        
        if book.get("status") == "issued":
            success, msg = await self.return_book(rfid)
            if success:
                result["action"] = "Автоматически оформлен возврат"
            else:
                result["status"] = "error"
                result["action"] = f"Ошибка авто-возврата: {msg}"
        else:
            result["action"] = "Книга корректно возвращена"
        
        return result
    
    async def verify_cabinet_inventory(self, expected_books: List[Dict]) -> Dict:
        """
        Сверка инвентаря шкафа с ИРБИС
        
        Args:
            expected_books: [{rfid, cell}, ...] - книги в шкафу
        
        Returns:
        {
            "total": int,
            "available": int,
            "issued": int,
            "not_found": int,
            "problems": [...]
        }
        """
        stats = {
            "total": len(expected_books),
            "available": 0,
            "issued": 0,
            "not_found": 0,
            "problems": [],
        }
        
        for book_info in expected_books:
            rfid = book_info.get("rfid", "")
            cell = book_info.get("cell")
            
            book = await self.irbis.get_book(rfid or "")
            
            if not book:
                stats["not_found"] += 1
                stats["problems"].append({
                    "rfid": rfid,
                    "cell": cell,
                    "issue": "Книга не найдена в каталоге"
                })
                continue
            
            status = book.get("status", "available")
            
            if status == "available":
                stats["available"] += 1
            elif status == "issued":
                stats["issued"] += 1
                stats["problems"].append({
                    "rfid": rfid,
                    "cell": cell,
                    "title": book.get("title", ""),
                    "issue": "Книга в шкафу, но числится выданной в ИРБИС"
                })
            else:
                stats["problems"].append({
                    "rfid": rfid,
                    "cell": cell,
                    "issue": f"Неизвестный статус: {status}"
                })
        
        return stats


library_service = LibraryService()
