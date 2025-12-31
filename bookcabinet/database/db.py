"""
SQLite база данных
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from ..config import DATABASE_PATH, CABINET, BLOCKED_CELLS
from .models import Cell, Book, User, Operation, SystemLog, CellStatus, BookStatus, UserRole


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cells (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    row TEXT NOT NULL,
                    x INTEGER NOT NULL,
                    y INTEGER NOT NULL,
                    status TEXT DEFAULT 'empty',
                    book_rfid TEXT,
                    book_title TEXT,
                    reserved_for TEXT,
                    needs_extraction BOOLEAN DEFAULT 0,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rfid TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT,
                    isbn TEXT,
                    status TEXT DEFAULT 'in_cabinet',
                    cell_id INTEGER,
                    reserved_by TEXT,
                    issued_to TEXT,
                    issued_at TEXT,
                    due_date TEXT,
                    FOREIGN KEY (cell_id) REFERENCES cells(id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rfid TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT DEFAULT 'reader',
                    card_type TEXT DEFAULT 'library',
                    active BOOLEAN DEFAULT 1
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    cell_row TEXT,
                    cell_x INTEGER,
                    cell_y INTEGER,
                    book_rfid TEXT,
                    user_rfid TEXT,
                    result TEXT DEFAULT 'OK',
                    duration_ms INTEGER DEFAULT 0,
                    details TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    component TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('SELECT COUNT(*) FROM cells')
            if cursor.fetchone()[0] == 0:
                self._init_cells(cursor)
            
            cursor.execute('SELECT COUNT(*) FROM users')
            if cursor.fetchone()[0] == 0:
                self._init_mock_data(cursor)
    
    def _init_cells(self, cursor):
        cell_id = 1
        for row in CABINET['rows']:
            for x in range(CABINET['columns']):
                for y in range(CABINET['positions']):
                    blocked = any(
                        b['x'] == x and b['y'] == y 
                        for b in BLOCKED_CELLS.get(row, [])
                    )
                    status = 'blocked' if blocked else 'empty'
                    cursor.execute('''
                        INSERT INTO cells (id, row, x, y, status, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (cell_id, row, x, y, status, datetime.now().isoformat()))
                    cell_id += 1
    
    def _init_mock_data(self, cursor):
        users = [
            ('CARD001', 'Иванов И.И.', 'reader', 'library'),
            ('CARD002', 'Петрова М.С.', 'reader', 'library'),
            ('ADMIN01', 'Козлова А.В.', 'librarian', 'library'),
            ('ADMIN99', 'Администратор', 'admin', 'library'),
        ]
        for rfid, name, role, card_type in users:
            cursor.execute('''
                INSERT INTO users (rfid, name, role, card_type)
                VALUES (?, ?, ?, ?)
            ''', (rfid, name, role, card_type))
        
        books = [
            ('BOOK001', 'Война и мир', 'Толстой Л.Н.', 'reserved', 'CARD001'),
            ('BOOK002', 'Мастер и Маргарита', 'Булгаков М.А.', 'in_cabinet', None),
            ('BOOK003', '1984', 'Оруэлл Дж.', 'reserved', 'CARD002'),
            ('BOOK004', 'Преступление и наказание', 'Достоевский Ф.М.', 'in_cabinet', None),
            ('BOOK005', 'Анна Каренина', 'Толстой Л.Н.', 'in_cabinet', None),
        ]
        
        cursor.execute("SELECT id FROM cells WHERE status = 'empty' LIMIT 5")
        empty_cells = [row[0] for row in cursor.fetchall()]
        
        for i, (rfid, title, author, status, reserved_by) in enumerate(books):
            cell_id = empty_cells[i] if i < len(empty_cells) else None
            cursor.execute('''
                INSERT INTO books (rfid, title, author, status, cell_id, reserved_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rfid, title, author, status, cell_id, reserved_by))
            
            if cell_id:
                cursor.execute('''
                    UPDATE cells SET status = 'occupied', book_rfid = ?, book_title = ?, reserved_for = ?
                    WHERE id = ?
                ''', (rfid, title, reserved_by, cell_id))

    def get_all_cells(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cells ORDER BY row, x, y')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_cell(self, cell_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cells WHERE id = ?', (cell_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_cell_by_position(self, row: str, x: int, y: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cells WHERE row = ? AND x = ? AND y = ?', (row, x, y))
            row_data = cursor.fetchone()
            return dict(row_data) if row_data else None
    
    def update_cell(self, cell_id: int, **kwargs) -> bool:
        kwargs['updated_at'] = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ', '.join(f'{k} = ?' for k in kwargs.keys())
            values = list(kwargs.values()) + [cell_id]
            cursor.execute(f'UPDATE cells SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0
    
    def find_empty_cell(self) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cells WHERE status = 'empty' LIMIT 1")
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_cells_needing_extraction(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cells WHERE needs_extraction = 1')
            return [dict(row) for row in cursor.fetchall()]

    def get_user_by_rfid(self, rfid: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE rfid = ? AND active = 1', (rfid,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_book_by_rfid(self, rfid: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM books WHERE rfid = ?', (rfid,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_reservations(self, user_rfid: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, c.row, c.x, c.y 
                FROM books b
                LEFT JOIN cells c ON b.cell_id = c.id
                WHERE b.reserved_by = ? AND b.status = 'reserved'
            ''', (user_rfid,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_book(self, book_id: int, **kwargs) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            set_clause = ', '.join(f'{k} = ?' for k in kwargs.keys())
            values = list(kwargs.values()) + [book_id]
            cursor.execute(f'UPDATE books SET {set_clause} WHERE id = ?', values)
            return cursor.rowcount > 0
    
    def create_book(self, rfid: str, title: str, author: str = None, cell_id: int = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO books (rfid, title, author, status, cell_id)
                VALUES (?, ?, ?, 'in_cabinet', ?)
            ''', (rfid, title, author, cell_id))
            return cursor.lastrowid

    def log_operation(self, operation: str, **kwargs) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO operations (timestamp, operation, cell_row, cell_x, cell_y, book_rfid, user_rfid, result, duration_ms, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                operation,
                kwargs.get('cell_row'),
                kwargs.get('cell_x'),
                kwargs.get('cell_y'),
                kwargs.get('book_rfid'),
                kwargs.get('user_rfid'),
                kwargs.get('result', 'OK'),
                kwargs.get('duration_ms', 0),
                kwargs.get('details'),
            ))
            return cursor.lastrowid
    
    def add_system_log(self, level: str, message: str, component: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_logs (timestamp, level, message, component)
                VALUES (?, ?, ?, ?)
            ''', (datetime.now().isoformat(), level, message, component))
            return cursor.lastrowid
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM system_logs ORDER BY id DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cells WHERE status = 'occupied'")
            occupied = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cells WHERE status != 'blocked'")
            available = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cells WHERE needs_extraction = 1")
            needs_extraction = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM operations WHERE operation = 'ISSUE'")
            total_issues = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM operations WHERE operation = 'RETURN'")
            total_returns = cursor.fetchone()[0]
            
            today = datetime.now().date().isoformat()
            cursor.execute("SELECT COUNT(*) FROM operations WHERE operation = 'ISSUE' AND timestamp LIKE ?", (f'{today}%',))
            issues_today = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM operations WHERE operation = 'RETURN' AND timestamp LIKE ?", (f'{today}%',))
            returns_today = cursor.fetchone()[0]
            
            return {
                'occupiedCells': occupied,
                'totalCells': available,
                'booksNeedExtraction': needs_extraction,
                'issuesTotal': total_issues,
                'issuesToday': issues_today,
                'returnsTotal': total_returns,
                'returnsToday': returns_today,
            }


db = Database()
