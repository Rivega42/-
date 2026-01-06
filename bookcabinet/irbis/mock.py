"""
Mock IRBIS64 для тестирования

Эмулирует структуру данных ИРБИС64:
- База RDR (читатели): поля 10 (ФИО), 30 (идентификатор), 40 (выдачи), 50 (категория)
- База IBIS (книги): поля 200 (название), 700 (автор), 903 (шифр), 910 (экземпляры)
"""
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from copy import deepcopy

from ..utils.irbis_helpers import (
    normalize_rfid, make_uid_variants, parse_subfields, format_subfields,
    get_field_value, get_field_values, find_exemplar_by_rfid,
    format_book_brief, get_active_loans, find_loan_by_rfid, generate_guid
)


class MockIrbis:
    """
    Mock реализация ИРБИС64 с правильной структурой данных
    """
    
    def __init__(self):
        self.readers_db = "RDR"
        self.books_db = "IBIS"
        self.loan_days = 30
        self.location_code = "09"
        self.username = "MASTER"
        self.connected = True
        
        self.readers = {
            1: {
                "mfn": 1,
                "fields": {
                    "10": ["^AИванов^BИван^GИванович"],
                    "30": ["CARD001"],
                    "50": ["Читатель"],
                    "40": [],
                }
            },
            2: {
                "mfn": 2,
                "fields": {
                    "10": ["^AПетрова^BМария^GСергеевна"],
                    "30": ["CARD002"],
                    "50": ["Читатель"],
                    "40": [],
                }
            },
            3: {
                "mfn": 3,
                "fields": {
                    "10": ["^AСидорова^BАнна^GВладимировна"],
                    "30": ["ADMIN01"],
                    "50": ["Библиотекарь"],
                    "40": [],
                }
            },
            4: {
                "mfn": 4,
                "fields": {
                    "10": ["^AАдминистратор^BСистемы"],
                    "30": ["ADMIN99"],
                    "50": ["Администратор"],
                    "40": [],
                }
            },
        }
        
        self.books = {
            1: {
                "mfn": 1,
                "fields": {
                    "200": ["^AВойна и мир"],
                    "700": ["^AТолстой^BЛ.^GН."],
                    "903": ["Р2"],
                    "910": ["^a0^b00001^c20200101^dАбонемент^hBOOK001"],
                }
            },
            2: {
                "mfn": 2,
                "fields": {
                    "200": ["^AМастер и Маргарита"],
                    "700": ["^AБулгаков^BМ.^GА."],
                    "903": ["Р2"],
                    "910": ["^a0^b00002^c20200101^dАбонемент^hBOOK002"],
                }
            },
            3: {
                "mfn": 3,
                "fields": {
                    "200": ["^A1984"],
                    "700": ["^AОруэлл^BДж."],
                    "903": ["И(Англ)"],
                    "910": ["^a0^b00003^c20200101^dАбонемент^hBOOK003"],
                }
            },
            4: {
                "mfn": 4,
                "fields": {
                    "200": ["^AПреступление и наказание"],
                    "700": ["^AДостоевский^BФ.^GМ."],
                    "903": ["Р2"],
                    "910": ["^a0^b00004^c20200101^dАбонемент^hBOOK004"],
                }
            },
            5: {
                "mfn": 5,
                "fields": {
                    "200": ["^AАнна Каренина"],
                    "700": ["^AТолстой^BЛ.^GН."],
                    "903": ["Р2"],
                    "910": ["^a0^b00005^c20200101^dАбонемент^hBOOK005"],
                }
            },
        }
        
        self.reader_index = {}
        self.book_index = {}
        self._build_indexes()
    
    def _build_indexes(self):
        """Построение индексов для поиска"""
        for mfn, reader in self.readers.items():
            for field30 in get_field_values(reader, "30"):
                normalized = normalize_rfid(field30)
                if normalized:
                    self.reader_index[normalized] = mfn
                    for variant in make_uid_variants(field30):
                        self.reader_index[variant.upper()] = mfn
        
        for mfn, book in self.books.items():
            for field910 in get_field_values(book, "910"):
                subfields = parse_subfields(field910)
                rfid = normalize_rfid(subfields.get("H", ""))
                if rfid:
                    self.book_index[rfid] = mfn
                    for variant in make_uid_variants(rfid):
                        self.book_index[variant.upper()] = mfn
    
    async def connect(self) -> bool:
        self.connected = True
        return True
    
    async def disconnect(self):
        self.connected = False
    
    async def check_connection(self) -> bool:
        return self.connected
    
    async def find_reader_by_card(self, card_uid: str) -> Optional[Dict]:
        """Поиск читателя по UID карты"""
        normalized = normalize_rfid(card_uid)
        if normalized and normalized in self.reader_index:
            mfn = self.reader_index[normalized]
            return deepcopy(self.readers.get(mfn))
        
        for variant in make_uid_variants(card_uid):
            if variant.upper() in self.reader_index:
                mfn = self.reader_index[variant.upper()]
                return deepcopy(self.readers.get(mfn))
        
        return None
    
    async def find_book_by_rfid(self, rfid: str) -> Optional[Dict]:
        """Поиск книги по RFID"""
        normalized = normalize_rfid(rfid)
        if normalized and normalized in self.book_index:
            mfn = self.book_index[normalized]
            return deepcopy(self.books.get(mfn))
        
        for variant in make_uid_variants(rfid):
            if variant.upper() in self.book_index:
                mfn = self.book_index[variant.upper()]
                return deepcopy(self.books.get(mfn))
        
        return None
    
    async def find_reader_with_book(self, book_rfid: str) -> Optional[Dict]:
        """Найти читателя с выданной книгой"""
        rfid = normalize_rfid(book_rfid)
        if not rfid:
            return None
        
        for mfn, reader in self.readers.items():
            for field40 in get_field_values(reader, "40"):
                subfields = parse_subfields(field40)
                if subfields.get("F") == "******":
                    loan_rfid = normalize_rfid(subfields.get("H", ""))
                    if loan_rfid == rfid:
                        return deepcopy(reader)
        
        return None
    
    async def get_user(self, rfid: str) -> Optional[Dict]:
        """Получить информацию о пользователе (совместимость)"""
        record = await self.find_reader_by_card(rfid)
        if not record:
            return None
        
        name = get_field_value(record, "10", "")
        if name:
            subfields = parse_subfields(name)
            name = f"{subfields.get('A', '')} {subfields.get('B', '')} {subfields.get('G', '')}".strip()
        
        category = get_field_value(record, "50", "").lower()
        role = "reader"
        if "библиотекарь" in category or "сотрудник" in category:
            role = "librarian"
        if "администратор" in category:
            role = "admin"
        
        return {
            "rfid": rfid,
            "name": name or "Читатель",
            "role": role,
            "mfn": record.get("mfn"),
        }
    
    async def get_book(self, rfid: str) -> Optional[Dict]:
        """Получить информацию о книге (совместимость)"""
        record = await self.find_book_by_rfid(rfid)
        if not record:
            return None
        
        title = format_book_brief(record)
        exemplar = find_exemplar_by_rfid(record, rfid)
        status = exemplar.get("status", "0") if exemplar else "0"
        
        return {
            "rfid": rfid,
            "title": title,
            "author": "",
            "status": "available" if status == "0" else "issued" if status == "1" else status,
            "mfn": record.get("mfn"),
        }
    
    async def get_reservations(self, user_rfid: str) -> List[Dict]:
        """Получить забронированные книги (совместимость)"""
        reader = await self.find_reader_by_card(user_rfid)
        if not reader:
            return []
        
        return get_active_loans(reader)
    
    async def register_issue(self, book_rfid: str, user_rfid: str) -> bool:
        """Регистрация выдачи (совместимость)"""
        success, _ = await self.issue_book(book_rfid, user_rfid)
        return success
    
    async def register_return(self, book_rfid: str) -> bool:
        """Регистрация возврата (совместимость)"""
        success, _ = await self.return_book(book_rfid)
        return success
    
    async def issue_book(self, book_rfid: str, reader_card: str) -> Tuple[bool, str]:
        """Полная процедура выдачи книги"""
        reader = await self.find_reader_by_card(reader_card)
        if not reader:
            return False, "Читатель не найден"
        
        book = await self.find_book_by_rfid(book_rfid)
        if not book:
            return False, "Книга не найдена"
        
        rfid = normalize_rfid(book_rfid) or ""
        exemplar = find_exemplar_by_rfid(book, rfid)
        if not exemplar:
            return False, "Экземпляр не найден"
        
        if exemplar["status"] == "1":
            return False, "Книга уже выдана"
        
        now = datetime.now()
        due_date = now + timedelta(days=self.loan_days)
        
        shelfmark = get_field_value(book, "903", "")
        title = format_book_brief(book)
        
        loan_record = format_subfields({
            "A": shelfmark,
            "B": exemplar["inventory"],
            "C": title[:100],
            "D": now.strftime("%Y%m%d"),
            "E": due_date.strftime("%Y%m%d"),
            "F": "******",
            "G": self.books_db,
            "H": rfid,
            "I": self.username,
            "K": exemplar["location"],
            "V": self.location_code,
            "Z": generate_guid(),
            "1": now.strftime("%H%M%S"),
        })
        
        mfn = reader["mfn"]
        if "40" not in self.readers[mfn]["fields"]:
            self.readers[mfn]["fields"]["40"] = []
        self.readers[mfn]["fields"]["40"].append(loan_record)
        
        book_mfn = book["mfn"]
        fields910 = self.books[book_mfn]["fields"].get("910", [])
        for i, field910 in enumerate(fields910):
            subfields = parse_subfields(field910)
            field_rfid = normalize_rfid(subfields.get("H", ""))
            if field_rfid == rfid:
                subfields["A"] = "1"
                fields910[i] = format_subfields(subfields)
                break
        self.books[book_mfn]["fields"]["910"] = fields910
        
        return True, f"Книга выдана: {title}"
    
    async def return_book(self, book_rfid: str) -> Tuple[bool, str]:
        """Полная процедура возврата книги"""
        reader = await self.find_reader_with_book(book_rfid)
        if not reader:
            book = await self.find_book_by_rfid(book_rfid)
            if book:
                exemplar = find_exemplar_by_rfid(book, book_rfid)
                if exemplar and exemplar["status"] == "0":
                    return True, "Книга уже возвращена"
            return False, "Книга не числится выданной"
        
        rfid = normalize_rfid(book_rfid)
        loan_index = find_loan_by_rfid(reader, rfid or "")
        if loan_index is None:
            return False, "Запись о выдаче не найдена"
        
        mfn = reader["mfn"]
        now = datetime.now()
        
        fields40 = self.readers[mfn]["fields"].get("40", [])
        if loan_index < len(fields40):
            subfields = parse_subfields(fields40[loan_index])
            
            if "C" in subfields:
                del subfields["C"]
            
            subfields["F"] = now.strftime("%Y%m%d")
            subfields["2"] = now.strftime("%H%M%S")
            subfields["R"] = self.location_code
            subfields["I"] = self.username
            
            subfields_clean: Dict[str, str] = {k: v for k, v in subfields.items() if v is not None}
            fields40[loan_index] = format_subfields(subfields_clean)
            self.readers[mfn]["fields"]["40"] = fields40
        
        book = await self.find_book_by_rfid(book_rfid)
        if book:
            book_mfn = book["mfn"]
            fields910 = self.books[book_mfn]["fields"].get("910", [])
            for i, field910 in enumerate(fields910):
                subfields = parse_subfields(field910)
                field_rfid = normalize_rfid(subfields.get("H", ""))
                if field_rfid == rfid:
                    subfields["A"] = "0"
                    fields910[i] = format_subfields(subfields)
                    break
            self.books[book_mfn]["fields"]["910"] = fields910
        
        return True, "Книга возвращена"


mock_irbis = MockIrbis()
