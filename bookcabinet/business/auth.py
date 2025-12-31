"""
Авторизация по карте
"""
from typing import Optional, Dict, List
from ..database import db
from ..irbis.mock import mock_irbis
from ..config import IRBIS


class AuthService:
    def __init__(self):
        self.irbis = mock_irbis if IRBIS['mock'] else None
    
    async def authenticate(self, card_rfid: str) -> Dict:
        user = db.get_user_by_rfid(card_rfid)
        
        if not user:
            if self.irbis:
                irbis_user = await self.irbis.get_user(card_rfid)
                if irbis_user:
                    user = irbis_user
        
        if not user:
            return {
                'success': False,
                'error': 'Пользователь не найден',
            }
        
        reservations = db.get_user_reservations(card_rfid)
        
        if self.irbis:
            irbis_reservations = await self.irbis.get_reservations(card_rfid)
            for res in irbis_reservations:
                if not any(r['rfid'] == res['rfid'] for r in reservations):
                    reservations.append(res)
        
        cells_extraction = db.get_cells_needing_extraction()
        
        db.add_system_log('INFO', f"Авторизация: {user['name']} ({user['role']})", 'auth')
        
        return {
            'success': True,
            'user': user,
            'reservedBooks': reservations,
            'needsExtraction': len(cells_extraction),
        }
    
    def check_permission(self, user: Dict, action: str) -> bool:
        from ..database.models import ROLE_PERMISSIONS, UserRole
        role = UserRole(user.get('role', 'reader'))
        permissions = ROLE_PERMISSIONS.get(role, [])
        return action in permissions


auth_service = AuthService()
