"""
Mock IRBIS64 для тестирования
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta


class MockIrbis:
    def __init__(self):
        self.users = {
            'CARD001': {'rfid': 'CARD001', 'name': 'Иванов И.И.', 'role': 'reader'},
            'CARD002': {'rfid': 'CARD002', 'name': 'Петрова М.С.', 'role': 'reader'},
            'ADMIN01': {'rfid': 'ADMIN01', 'name': 'Козлова А.В.', 'role': 'librarian'},
            'ADMIN99': {'rfid': 'ADMIN99', 'name': 'Администратор', 'role': 'admin'},
        }
        
        self.books = {
            'BOOK001': {'rfid': 'BOOK001', 'title': 'Война и мир', 'author': 'Толстой Л.Н.', 'isbn': '978-5-17-090000-1'},
            'BOOK002': {'rfid': 'BOOK002', 'title': 'Мастер и Маргарита', 'author': 'Булгаков М.А.', 'isbn': '978-5-17-090000-2'},
            'BOOK003': {'rfid': 'BOOK003', 'title': '1984', 'author': 'Оруэлл Дж.', 'isbn': '978-5-17-090000-3'},
            'BOOK004': {'rfid': 'BOOK004', 'title': 'Преступление и наказание', 'author': 'Достоевский Ф.М.', 'isbn': '978-5-17-090000-4'},
            'BOOK005': {'rfid': 'BOOK005', 'title': 'Анна Каренина', 'author': 'Толстой Л.Н.', 'isbn': '978-5-17-090000-5'},
        }
        
        self.reservations = {
            'CARD001': ['BOOK001'],
            'CARD002': ['BOOK003'],
        }
        
        self.issues = {}
    
    async def connect(self) -> bool:
        return True
    
    async def disconnect(self):
        pass
    
    async def get_user(self, rfid: str) -> Optional[Dict]:
        return self.users.get(rfid)
    
    async def get_book(self, rfid: str) -> Optional[Dict]:
        return self.books.get(rfid)
    
    async def get_reservations(self, user_rfid: str) -> List[Dict]:
        reserved = self.reservations.get(user_rfid, [])
        return [self.books[rfid] for rfid in reserved if rfid in self.books]
    
    async def register_issue(self, book_rfid: str, user_rfid: str) -> bool:
        if book_rfid in self.books:
            self.issues[book_rfid] = {
                'user_rfid': user_rfid,
                'issued_at': datetime.now().isoformat(),
                'due_date': (datetime.now() + timedelta(days=14)).isoformat(),
            }
            if user_rfid in self.reservations and book_rfid in self.reservations[user_rfid]:
                self.reservations[user_rfid].remove(book_rfid)
            return True
        return False
    
    async def register_return(self, book_rfid: str) -> bool:
        if book_rfid in self.issues:
            del self.issues[book_rfid]
            return True
        return True
    
    async def check_connection(self) -> bool:
        return True


mock_irbis = MockIrbis()
