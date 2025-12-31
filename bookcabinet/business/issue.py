"""
Выдача книги
"""
from typing import Dict
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..irbis.mock import mock_irbis
from ..config import IRBIS


class IssueService:
    def __init__(self):
        self.irbis = mock_irbis if IRBIS['mock'] else None
    
    async def issue_book(self, book_rfid: str, user_rfid: str, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        book = db.get_book_by_rfid(book_rfid)
        if not book:
            return {'success': False, 'error': 'Книга не найдена'}
        
        if book['status'] == 'issued':
            return {'success': False, 'error': 'Книга уже выдана'}
        
        if book['reserved_by'] and book['reserved_by'] != user_rfid:
            return {'success': False, 'error': 'Книга забронирована другим читателем'}
        
        cell = db.get_cell(book['cell_id']) if book.get('cell_id') else None
        if not cell:
            return {'success': False, 'error': 'Книга не в шкафу'}
        
        if on_progress:
            algorithms.set_callbacks(progress=on_progress)
        
        success = await algorithms.take_shelf(cell['row'], cell['x'], cell['y'])
        if not success:
            return {'success': False, 'error': 'Ошибка механики шкафа'}
        
        await algorithms.wait_for_user()
        
        await algorithms.give_shelf(cell['row'], cell['x'], cell['y'])
        
        db.update_book(book['id'],
            status='issued',
            issued_to=user_rfid,
            issued_at=datetime.now().isoformat(),
            reserved_by=None,
            cell_id=None
        )
        
        db.update_cell(cell['id'],
            status='empty',
            book_rfid=None,
            book_title=None,
            reserved_for=None
        )
        
        if self.irbis:
            await self.irbis.register_issue(book_rfid, user_rfid)
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        db.log_operation('ISSUE',
            cell_row=cell['row'],
            cell_x=cell['x'],
            cell_y=cell['y'],
            book_rfid=book_rfid,
            user_rfid=user_rfid,
            duration_ms=duration
        )
        
        db.add_system_log('INFO', f"Выдана книга: {book['title']}", 'issue')
        
        return {
            'success': True,
            'book': book,
            'message': f'Книга "{book["title"]}" выдана'
        }


issue_service = IssueService()
