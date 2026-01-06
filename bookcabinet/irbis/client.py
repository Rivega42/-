"""
IRBIS64 TCP Client - Полноценная реализация протокола

Протокол ИРБИС64:
- TCP порт 6666 (по умолчанию)
- Команды: A (connect), B (disconnect), K (search), C (read), D (write), G (format)
- Формат запроса: [длина]\r\n[данные]
- Формат ответа: [код]\r\n[данные]
"""
import asyncio
import socket
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from ..config import IRBIS
from ..utils.irbis_helpers import (
    normalize_rfid, make_uid_variants, parse_subfields, format_subfields,
    parse_record, format_record, get_field_value, get_field_values,
    find_exemplar_by_rfid, format_book_brief, get_active_loans,
    find_loan_by_rfid, generate_guid
)


@dataclass
class IrbisConfig:
    """Конфигурация подключения к ИРБИС64"""
    host: str = "127.0.0.1"
    port: int = 6666
    username: str = "MASTER"
    password: str = "MASTERKEY"
    database: str = "IBIS"
    readers_database: str = "RDR"
    workstation: str = "C"
    loan_days: int = 30
    location_code: str = "09"


@dataclass
class IrbisResponse:
    """Ответ сервера ИРБИС"""
    return_code: int
    data: str
    
    @property
    def success(self) -> bool:
        return self.return_code >= 0


class IrbisClient:
    """
    Клиент для работы с ИРБИС64 по TCP протоколу
    
    Коды команд:
        A - Регистрация клиента
        B - Разрегистрация
        C - Чтение записи
        D - Сохранение записи
        K - Поиск
        G - Форматирование
    
    Коды возврата:
        >= 0 - Успех (количество записей или MFN)
        -1   - Сервер выполняет обновление
        -2   - Ошибка БД
        -3   - Сервер недоступен
        -4   - Неверный клиент
        -140 - Запись логически удалена
        -201 - Запись заблокирована
        -600 - Пользователь не зарегистрирован
        -601 - Неверный пароль
    """
    
    def __init__(self, config: Optional[IrbisConfig] = None):
        self.config = config if config else IrbisConfig(
            host=IRBIS.get('host', '127.0.0.1'),
            port=IRBIS.get('port', 6666),
            username=IRBIS.get('username', 'MASTER'),
            password=IRBIS.get('password', 'MASTERKEY'),
        )
        self.client_id = 100000 + int(datetime.now().timestamp() % 100000)
        self.sequence = 1
        self.connected = False
    
    async def connect(self) -> bool:
        """Подключение к серверу ИРБИС (команда A)"""
        try:
            response = await self._execute_command("A", [
                self.config.username,
                self.config.password,
            ])
            self.connected = response.success
            return self.connected
        except Exception as e:
            print(f"IRBIS connection error: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Отключение от сервера (команда B)"""
        if self.connected:
            try:
                await self._execute_command("B", [self.config.username])
            except:
                pass
            self.connected = False
    
    async def search(self, database: str, expression: str) -> List[int]:
        """
        Поиск записей (команда K)
        
        Args:
            database: Имя базы данных (IBIS, RDR)
            expression: Поисковое выражение (например, "RI=ABCD1234")
        
        Returns:
            Список MFN найденных записей
        """
        response = await self._execute_command("K", [
            database,
            expression,
            "0",
            "1",
        ])
        
        if not response.success:
            return []
        
        mfn_list = []
        for line in response.data.split("\r\n"):
            line = line.strip()
            if line.isdigit():
                mfn_list.append(int(line))
        
        return mfn_list
    
    async def read_record(self, database: str, mfn: int) -> Optional[Dict]:
        """
        Чтение записи по MFN (команда C)
        
        Args:
            database: Имя базы данных
            mfn: Номер записи
        
        Returns:
            Словарь с полями записи или None
        """
        response = await self._execute_command("C", [
            database,
            str(mfn),
        ])
        
        if not response.success:
            return None
        
        record = parse_record(response.data)
        if record:
            record["mfn"] = mfn
        return record
    
    async def search_read(self, database: str, expression: str) -> List[Dict]:
        """
        Поиск и чтение записей одной командой
        
        Args:
            database: Имя базы данных
            expression: Поисковое выражение
        
        Returns:
            Список записей
        """
        response = await self._execute_command("K", [
            database,
            expression,
            "0",
            "1",
            "@",
        ])
        
        if not response.success:
            return []
        
        records = []
        for record_text in response.data.split("\x1D"):
            if record_text.strip():
                record = parse_record(record_text)
                if record:
                    records.append(record)
        
        return records
    
    async def write_record(self, database: str, record: Dict) -> bool:
        """
        Запись/обновление записи (команда D)
        
        Args:
            database: Имя базы данных
            record: Словарь с полями записи
        
        Returns:
            True при успехе
        """
        record_text = format_record(record)
        response = await self._execute_command("D", [
            database,
            "0",
            "1",
            record_text,
        ])
        return response.success
    
    async def format_record(self, database: str, mfn: int, format_str: str) -> str:
        """
        Форматирование записи (команда G)
        
        Args:
            database: Имя базы данных
            mfn: Номер записи
            format_str: Строка форматирования
        
        Returns:
            Отформатированный текст
        """
        response = await self._execute_command("G", [
            database,
            str(mfn),
            format_str,
        ])
        return response.data if response.success else ""
    
    async def find_reader_by_card(self, card_uid: str) -> Optional[Dict]:
        """
        Поиск читателя по UID карты
        
        Пробует различные варианты UID и индексы поиска:
        - RI= (Reader ID)
        - EKP= (Единая карта петербуржца)
        """
        if not card_uid:
            return None
        
        patterns = ['"RI={0}"', '"EKP={0}"']
        
        for uid_variant in make_uid_variants(card_uid):
            for pattern in patterns:
                expr = pattern.format(uid_variant)
                records = await self.search_read(self.config.readers_database, expr)
                
                if records:
                    return records[0]
        
        return None
    
    async def find_book_by_rfid(self, rfid: str) -> Optional[Dict]:
        """
        Поиск книги по RFID метке
        
        Пробует индексы:
        - H= (по полю 910^h)
        - HI= (альтернативный)
        - RF= / RFID= (если настроен)
        """
        if not rfid:
            return None
        
        patterns = ['"H={0}"', '"HI={0}"', '"RF={0}"', '"RFID={0}"']
        
        for rfid_variant in make_uid_variants(rfid):
            for pattern in patterns:
                expr = pattern.format(rfid_variant)
                records = await self.search_read(self.config.database, expr)
                
                if records:
                    return records[0]
        
        return None
    
    async def find_reader_with_book(self, book_rfid: str) -> Optional[Dict]:
        """
        Найти читателя, которому выдана книга
        
        Индекс: HIN= (по полю 40^H)
        """
        if not book_rfid:
            return None
        
        for rfid_variant in make_uid_variants(book_rfid):
            expr = f'"HIN={rfid_variant}"'
            records = await self.search_read(self.config.readers_database, expr)
            
            if records:
                return records[0]
        
        return None
    
    async def _execute_command(self, command: str, params: List[str]) -> IrbisResponse:
        """
        Выполнение команды на сервере ИРБИС64
        
        Формат запроса:
            [команда]\r\n
            [workstation]\r\n
            [command_code]\r\n
            [client_id]\r\n
            [sequence]\r\n
            [password]\r\n
            [username]\r\n
            [пустые строки...]\r\n
            [параметры...]\r\n
        """
        lines = [
            command,
            self.config.workstation,
            command,
            str(self.client_id),
            str(self.sequence),
            self.config.password,
            self.config.username,
            "",
            "",
            "",
        ]
        lines.extend(params)
        
        request = "\r\n".join(lines)
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.host, self.config.port),
                timeout=10.0
            )
            
            data = request.encode("utf-8")
            header = f"{len(data)}\r\n".encode("utf-8")
            writer.write(header + data)
            await writer.drain()
            
            response_data = b""
            while True:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=30.0)
                if not chunk:
                    break
                response_data += chunk
                if len(chunk) < 4096:
                    break
            
            writer.close()
            await writer.wait_closed()
            
            self.sequence += 1
            
            response_text = response_data.decode("utf-8", errors="replace")
            return self._parse_response(response_text)
            
        except asyncio.TimeoutError:
            return IrbisResponse(-3, "Connection timeout")
        except ConnectionRefusedError:
            return IrbisResponse(-3, "Connection refused")
        except Exception as e:
            return IrbisResponse(-3, str(e))
    
    def _parse_response(self, text: str) -> IrbisResponse:
        """Парсинг ответа сервера"""
        lines = text.split("\r\n")
        
        return_code = -1
        if lines and lines[0].lstrip("-").isdigit():
            return_code = int(lines[0])
        
        data = "\r\n".join(lines[1:]) if len(lines) > 1 else ""
        
        return IrbisResponse(return_code, data)
    
    async def get_user(self, rfid: str) -> Optional[Dict]:
        """
        Получить информацию о пользователе по RFID карты
        (Совместимость с предыдущим API)
        """
        record = await self.find_reader_by_card(rfid)
        if not record:
            return None
        
        name = get_field_value(record, "10", "")
        if name:
            subfields = parse_subfields(name)
            name = f"{subfields.get('A', '')} {subfields.get('B', '')} {subfields.get('G', '')}".strip()
        
        role = "reader"
        category = get_field_value(record, "50", "")
        if "сотрудник" in category.lower() or "библиотекарь" in category.lower():
            role = "librarian"
        if "администратор" in category.lower():
            role = "admin"
        
        return {
            "rfid": rfid,
            "name": name or "Читатель",
            "role": role,
            "mfn": record.get("mfn"),
            "record": record,
        }
    
    async def get_book(self, rfid: str) -> Optional[Dict]:
        """
        Получить информацию о книге по RFID
        (Совместимость с предыдущим API)
        """
        record = await self.find_book_by_rfid(rfid)
        if not record:
            return None
        
        title = format_book_brief(record)
        
        exemplar = find_exemplar_by_rfid(record, rfid)
        status = exemplar.get("status", "0") if exemplar else "0"
        inventory = exemplar.get("inventory", "") if exemplar else ""
        
        shelfmark = get_field_value(record, "903", "")
        
        return {
            "rfid": rfid,
            "title": title,
            "author": "",
            "shelfmark": shelfmark,
            "inventory": inventory,
            "status": "available" if status == "0" else "issued" if status == "1" else status,
            "mfn": record.get("mfn"),
            "record": record,
        }
    
    async def get_reservations(self, user_rfid: str) -> List[Dict]:
        """
        Получить список забронированных книг для пользователя
        (Совместимость с предыдущим API)
        
        В ИРБИС нет стандартного механизма бронирования.
        Возвращает активные выдачи (книги на руках).
        """
        reader = await self.find_reader_by_card(user_rfid)
        if not reader:
            return []
        
        return get_active_loans(reader)
    
    async def register_issue(self, book_rfid: str, user_rfid: str) -> bool:
        """
        Регистрация выдачи книги
        (Совместимость с предыдущим API)
        """
        success, _ = await self.issue_book(book_rfid, user_rfid)
        return success
    
    async def register_return(self, book_rfid: str) -> bool:
        """
        Регистрация возврата книги
        (Совместимость с предыдущим API)
        """
        success, _ = await self.return_book(book_rfid)
        return success
    
    async def issue_book(self, book_rfid: str, reader_card: str) -> Tuple[bool, str]:
        """
        Полная процедура выдачи книги
        
        1. Найти читателя по карте
        2. Найти книгу по RFID
        3. Проверить статус экземпляра
        4. Добавить запись в поле 40 читателя
        5. Изменить статус экземпляра (910^a = "1")
        """
        reader = await self.find_reader_by_card(reader_card)
        if not reader:
            return False, "Читатель не найден"
        
        book = await self.find_book_by_rfid(book_rfid)
        if not book:
            return False, "Книга не найдена"
        
        rfid = normalize_rfid(book_rfid) or ""
        exemplar = find_exemplar_by_rfid(book, rfid)
        if not exemplar:
            return False, "Экземпляр с данной RFID не найден"
        
        if exemplar["status"] == "1":
            return False, "Книга уже выдана"
        
        if exemplar["status"] not in ["0", ""]:
            return False, f"Книга недоступна (статус: {exemplar['status']})"
        
        now = datetime.now()
        from datetime import timedelta
        due_date = now + timedelta(days=self.config.loan_days)
        
        shelfmark = get_field_value(book, "903", "")
        title = format_book_brief(book)
        
        loan_record = format_subfields({
            "A": shelfmark,
            "B": exemplar["inventory"],
            "C": title[:100],
            "D": now.strftime("%Y%m%d"),
            "E": due_date.strftime("%Y%m%d"),
            "F": "******",
            "G": self.config.database,
            "H": rfid,
            "I": self.config.username,
            "K": exemplar["location"],
            "V": self.config.location_code,
            "Z": generate_guid(),
            "1": now.strftime("%H%M%S"),
        })
        
        if "40" not in reader["fields"]:
            reader["fields"]["40"] = []
        reader["fields"]["40"].append(loan_record)
        
        if not await self.write_record(self.config.readers_database, reader):
            return False, "Ошибка записи выдачи"
        
        fields910 = get_field_values(book, "910")
        for i, field910 in enumerate(fields910):
            subfields = parse_subfields(field910)
            field_rfid = normalize_rfid(subfields.get("H", ""))
            if field_rfid == rfid:
                subfields["A"] = "1"
                fields910[i] = format_subfields(subfields)
                break
        book["fields"]["910"] = fields910
        
        if not await self.write_record(self.config.database, book):
            return False, "Ошибка обновления статуса книги"
        
        return True, f"Книга выдана: {title}"
    
    async def return_book(self, book_rfid: str) -> Tuple[bool, str]:
        """
        Полная процедура возврата книги
        
        1. Найти читателя с этой книгой (HIN=)
        2. Найти запись о выдаче в поле 40
        3. Закрыть запись (установить ^F = дата)
        4. Изменить статус экземпляра (910^a = "0")
        """
        reader = await self.find_reader_with_book(book_rfid)
        if not reader:
            book = await self.find_book_by_rfid(book_rfid)
            if book:
                exemplar = find_exemplar_by_rfid(book, book_rfid)
                if exemplar and exemplar["status"] == "0":
                    return True, "Книга уже возвращена"
            return False, "Книга не числится выданной"
        
        rfid = normalize_rfid(book_rfid) or ""
        loan_index = find_loan_by_rfid(reader, rfid)
        if loan_index is None:
            return False, "Запись о выдаче не найдена"
        
        now = datetime.now()
        fields40 = get_field_values(reader, "40")
        subfields = parse_subfields(fields40[loan_index])
        
        if "C" in subfields:
            del subfields["C"]
        
        subfields["F"] = now.strftime("%Y%m%d")
        subfields["2"] = now.strftime("%H%M%S")
        subfields["R"] = self.config.location_code
        subfields["I"] = self.config.username
        
        subfields_clean: Dict[str, str] = {k: v for k, v in subfields.items() if v is not None}
        fields40[loan_index] = format_subfields(subfields_clean)
        reader["fields"]["40"] = fields40
        
        if not await self.write_record(self.config.readers_database, reader):
            return False, "Ошибка закрытия выдачи"
        
        book = await self.find_book_by_rfid(book_rfid)
        if book:
            fields910 = get_field_values(book, "910")
            for i, field910 in enumerate(fields910):
                sub = parse_subfields(field910)
                field_rfid = normalize_rfid(sub.get("H", ""))
                if field_rfid == rfid:
                    sub["A"] = "0"
                    fields910[i] = format_subfields(sub)
                    break
            book["fields"]["910"] = fields910
            await self.write_record(self.config.database, book)
        
        return True, "Книга возвращена"
    
    async def check_connection(self) -> bool:
        """Проверка подключения"""
        return self.connected


irbis_client = IrbisClient()
