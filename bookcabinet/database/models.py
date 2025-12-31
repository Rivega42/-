"""
Модели данных для SQLite
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CellStatus(str, Enum):
    EMPTY = 'empty'
    OCCUPIED = 'occupied'
    BLOCKED = 'blocked'


class BookStatus(str, Enum):
    IN_CABINET = 'in_cabinet'
    RESERVED = 'reserved'
    ISSUED = 'issued'
    RETURNED = 'returned'


class UserRole(str, Enum):
    READER = 'reader'
    LIBRARIAN = 'librarian'
    ADMIN = 'admin'


class OperationType(str, Enum):
    INIT = 'INIT'
    TAKE = 'TAKE'
    GIVE = 'GIVE'
    ISSUE = 'ISSUE'
    RETURN = 'RETURN'
    LOAD = 'LOAD'
    EXTRACT = 'EXTRACT'


class OperationResult(str, Enum):
    OK = 'OK'
    ERROR = 'ERROR'


@dataclass
class Cell:
    id: int
    row: str
    x: int
    y: int
    status: CellStatus = CellStatus.EMPTY
    book_rfid: Optional[str] = None
    book_title: Optional[str] = None
    reserved_for: Optional[str] = None
    needs_extraction: bool = False
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Book:
    id: int
    rfid: str
    title: str
    author: Optional[str] = None
    isbn: Optional[str] = None
    status: BookStatus = BookStatus.IN_CABINET
    cell_id: Optional[int] = None
    reserved_by: Optional[str] = None
    issued_to: Optional[str] = None
    issued_at: Optional[str] = None
    due_date: Optional[str] = None


@dataclass
class User:
    id: int
    rfid: str
    name: str
    role: UserRole = UserRole.READER
    card_type: str = 'library'
    active: bool = True


@dataclass
class Operation:
    id: int
    timestamp: str
    operation: OperationType
    cell_row: Optional[str] = None
    cell_x: Optional[int] = None
    cell_y: Optional[int] = None
    book_rfid: Optional[str] = None
    user_rfid: Optional[str] = None
    result: OperationResult = OperationResult.OK
    duration_ms: int = 0
    details: Optional[str] = None


@dataclass
class SystemLog:
    id: int
    timestamp: str
    level: str
    message: str
    component: Optional[str] = None


@dataclass
class Settings:
    key: str
    value: str
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CalibrationData:
    kinematics: dict = field(default_factory=lambda: {
        'x_plus_dir_a': 1, 'x_plus_dir_b': -1,
        'y_plus_dir_a': 1, 'y_plus_dir_b': 1
    })
    positions_x: List[int] = field(default_factory=lambda: [0, 4500, 9000])
    positions_y: List[int] = field(default_factory=lambda: [i * 450 for i in range(21)])
    window: dict = field(default_factory=lambda: {'x': 1, 'y': 9})
    grab_front: dict = field(default_factory=lambda: {'extend1': 1500, 'retract': 1500, 'extend2': 3000})
    grab_back: dict = field(default_factory=lambda: {'extend1': 1500, 'retract': 1500, 'extend2': 3000})


# Роли и разрешения
ROLE_PERMISSIONS = {
    UserRole.READER: ['issue', 'return'],
    UserRole.LIBRARIAN: ['issue', 'return', 'load', 'unload', 'inventory'],
    UserRole.ADMIN: ['issue', 'return', 'load', 'unload', 'inventory', 'calibrate', 'settings', 'maintenance'],
}
