"""
Изъятие книги из шкафа (библиотекарь)
"""
from typing import Dict, List
from datetime import datetime

from ..database import db
from ..mechanics.algorithms import algorithms


class UnloadService:
    async def extract_book(self, cell_id: int, on_progress=None) -> Dict:
        start_time = datetime.now()
        
        cell = db.get_cell(cell_id)
        if not cell:
            return {'success': False, 'error': 'Ячейка не найдена'}
        
        if cell['status'] != 'occupied':
            return {'success': False, 'error': 'Ячейка пуста'}
        
        if on_progress:
            algorithms.set_callbacks(progress=on_progress)
        
        success = await algorithms.take_shelf(cell['row'], cell['x'], cell['y'])
        if not success:
            return {'success': False, 'error': 'Ошибка механики шкафа'}
        
        await algorithms.wait_for_user()
        
        await algorithms.give_shelf(cell['row'], cell['x'], cell['y'])
        
        book = db.get_book_by_rfid(cell['book_rfid']) if cell.get('book_rfid') else None
        
        if book:
            db.update_book(book['id'],
                status='extracted',
                cell_id=None
            )
        
        db.update_cell(cell_id,
            status='empty',
            book_rfid=None,
            book_title=None,
            reserved_for=None,
            needs_extraction=False
        )
        
        duration = int((datetime.now() - start_time).total_seconds() * 1000)
        db.log_operation('EXTRACT',
            cell_row=cell['row'],
            cell_x=cell['x'],
            cell_y=cell['y'],
            book_rfid=cell.get('book_rfid'),
            duration_ms=duration
        )
        
        title = cell.get('book_title', 'книга')
        db.add_system_log('INFO', f"Изъята книга: {title}", 'unload')
        
        return {
            'success': True,
            'book': book,
            'cell': cell,
            'message': f'Книга "{title}" изъята'
        }
    
    async def extract_all(self, on_progress=None) -> Dict:
        cells = db.get_cells_needing_extraction()
        
        if not cells:
            return {'success': True, 'extracted': 0, 'message': 'Нет книг для изъятия'}
        
        extracted = 0
        errors = []
        
        for cell in cells:
            result = await self.extract_book(cell['id'], on_progress)
            if result['success']:
                extracted += 1
            else:
                errors.append(f"Ячейка {cell['id']}: {result['error']}")
        
        return {
            'success': len(errors) == 0,
            'extracted': extracted,
            'errors': errors,
            'message': f'Изъято {extracted} книг'
        }
    
    async def run_inventory(self) -> Dict:
        cells = db.get_all_cells()
        
        found = 0
        missing = 0
        
        for cell in cells:
            if cell['status'] == 'occupied':
                found += 1
        
        db.add_system_log('INFO', f"Инвентаризация: найдено {found}, отсутствует {missing}", 'inventory')
        
        return {
            'success': True,
            'found': found,
            'missing': missing,
            'total': len(cells),
            'message': f'Инвентаризация завершена: найдено {found} книг'
        }


unload_service = UnloadService()
