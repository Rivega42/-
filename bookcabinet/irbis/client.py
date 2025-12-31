"""
IRBIS64 TCP Client
"""
import asyncio
from typing import Optional, Dict, List
from ..config import IRBIS


class IrbisClient:
    def __init__(self):
        self.host = IRBIS['host']
        self.port = IRBIS['port']
        self.connected = False
        self.reader = None
        self.writer = None
    
    async def connect(self) -> bool:
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            self.connected = True
            return True
        except Exception as e:
            print(f"IRBIS connection error: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
    
    async def _send_command(self, command: str) -> Optional[str]:
        if not self.connected:
            return None
        
        try:
            self.writer.write(command.encode('utf-8'))
            await self.writer.drain()
            
            response = await asyncio.wait_for(
                self.reader.read(4096),
                timeout=10.0
            )
            return response.decode('utf-8')
        except Exception as e:
            print(f"IRBIS command error: {e}")
            return None
    
    async def get_user(self, rfid: str) -> Optional[Dict]:
        response = await self._send_command(f"GET_USER {rfid}")
        if response:
            return {'rfid': rfid, 'name': 'User', 'role': 'reader'}
        return None
    
    async def get_book(self, rfid: str) -> Optional[Dict]:
        response = await self._send_command(f"GET_BOOK {rfid}")
        if response:
            return {'rfid': rfid, 'title': 'Book', 'author': 'Author'}
        return None
    
    async def get_reservations(self, user_rfid: str) -> List[Dict]:
        response = await self._send_command(f"GET_RESERVATIONS {user_rfid}")
        return []
    
    async def register_issue(self, book_rfid: str, user_rfid: str) -> bool:
        response = await self._send_command(f"ISSUE {book_rfid} {user_rfid}")
        return response is not None
    
    async def register_return(self, book_rfid: str) -> bool:
        response = await self._send_command(f"RETURN {book_rfid}")
        return response is not None


irbis_client = IrbisClient()
