"""
Загрузка книги в шкаф (библиотекарь)
"""
from typing import Dict, Optional
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..irbis.mock import mock_irbis
from ..config import IRBIS


class LoadService:
    def __init__(self):
        self.irbis = mock_irbis if IRBIS['mock'] else None
    
    async def load_book(self, book_rfid: str, title: str = None, author: str = None, 
                        cell_id: int = None, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        book = db.get_book_by_rfid(book_rfid)
        
        if not book:
            if not title:
                if self.irbis:
                    book_info = await self.irbis.get_book(book_rfid)
                    if book_info:
                        title = book_info.get('title', 'Без названия')
                        author = book_info.get('author')
                else:
                    return {'success': False, 'error': 'Укажите название книги'}
            
            book_id = db.create_book(book_rfid, title, author)
            book = db.get_book_by_rfid(book_rfid)
        
        if cell_id:
            cell = db.get_cell(cell_id)
            if not cell or cell['status'] != 'empty':
                return {'success': False, 'error': 'Ячейка недоступна'}
        else:
            cell = db.find_empty_cell()
            if not cell:
                return {'success': False, 'error': 'Нет свободных ячеек'}
        
        if on_progress:
            algorithms.set_callbacks(progress=on_progress)
        
        success = await algorithms.give_shelf(cell['row'], cell['x'], cell['y'])
        if not success:
            return {'success': False, 'error': 'Ошибка механики шкафа'}
        
        db.update_book(book['id'],
            status='in_cabinet',
            cell_id=cell['id']
        )
        
        db.update_cell(cell['id'],
            status='occupied',
            book_rfid=book_rfid,
            book_title=book['title']
        )
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        db.log_operation('LOAD',
            cell_row=cell['row'],
            cell_x=cell['x'],
            cell_y=cell['y'],
            book_rfid=book_rfid,
            duration_ms=duration
        )
        
        db.add_system_log('INFO', f"Загружена книга: {book['title']} в ячейку ({cell['row']}, {cell['x']}, {cell['y']})", 'load')
        
        return {
            'success': True,
            'book': book,
            'cell': cell,
            'message': f'Книга загружена в ячейку'
        }


load_service = LoadService()
