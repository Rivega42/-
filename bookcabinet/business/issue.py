"""
Выдача книги
"""
from typing import Dict
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms
from ..irbis.service import library_service


class IssueService:
    def __init__(self):
        self.irbis = library_service
    
    async def issue_book(self, book_rfid: str, user_rfid: str, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        book = db.get_book_by_rfid(book_rfid)
        if not book:
            irbis_book = await self.irbis.get_book_info(book_rfid)
            if not irbis_book:
                return {'success': False, 'error': 'Книга не найдена'}
            return {'success': False, 'error': 'Книга не загружена в шкаф'}
        
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
        
        irbis_success, irbis_msg = await self.irbis.issue_book(book_rfid, user_rfid)
        if not irbis_success:
            db.add_system_log('WARNING', f"ИРБИС: {irbis_msg}", 'issue')
        
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
