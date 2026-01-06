"""
Возврат книги
"""
from typing import Dict, Optional
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..irbis.service import library_service


class ReturnService:
    def __init__(self):
        self.irbis = library_service
    
    async def return_book(self, book_rfid: str, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        book = db.get_book_by_rfid(book_rfid)
        
        if not book:
            book_info = await self.irbis.get_book_info(book_rfid)
            
            if not book_info:
                return {'success': False, 'error': 'Книга не найдена в системе'}
            
            cell = db.find_empty_cell()
            if not cell:
                return {'success': False, 'error': 'Нет свободных ячеек'}
            
            title = book_info.get('title', 'Неизвестная книга')
            author = book_info.get('author', '')
            book_id = db.create_book(book_rfid, title, author or '')
            book = db.get_book_by_rfid(book_rfid)
            
            if not book:
                return {'success': False, 'error': 'Ошибка создания записи книги'}
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
        
        irbis_success, irbis_msg = await self.irbis.return_book(book_rfid)
        if not irbis_success:
            db.add_system_log('WARNING', f"ИРБИС: {irbis_msg}", 'return')
        
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
