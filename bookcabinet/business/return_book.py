"""
Возврат книги
"""
from typing import Dict
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..irbis.mock import mock_irbis
from ..config import IRBIS


class ReturnService:
    def __init__(self):
        self.irbis = mock_irbis if IRBIS['mock'] else None
    
    async def return_book(self, book_rfid: str, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        book = db.get_book_by_rfid(book_rfid)
        
        if not book:
            book_info = None
            if self.irbis:
                book_info = await self.irbis.get_book(book_rfid)
            
            if not book_info:
                return {'success': False, 'error': 'Книга не найдена в системе'}
            
            cell = db.find_empty_cell()
            if not cell:
                return {'success': False, 'error': 'Нет свободных ячеек'}
            
            book_id = db.create_book(book_rfid, book_info['title'], book_info.get('author'))
            book = db.get_book_by_rfid(book_rfid)
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
            status='returned',
            cell_id=cell['id'],
            issued_to=None,
            issued_at=None
        )
        
        db.update_cell(cell['id'],
            status='occupied',
            book_rfid=book_rfid,
            book_title=book['title'],
            needs_extraction=True
        )
        
        if self.irbis:
            await self.irbis.register_return(book_rfid)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        db.log_operation('RETURN',
            cell_row=cell['row'],
            cell_x=cell['x'],
            cell_y=cell['y'],
            book_rfid=book_rfid,
            duration_ms=duration
        )
        
        db.add_system_log('INFO', f"Возвращена книга: {book['title']}", 'return')
        
        return {
            'success': True,
            'book': book,
            'cell': cell,
            'message': f'Книга "{book["title"]}" возвращена'
        }


return_service = ReturnService()
