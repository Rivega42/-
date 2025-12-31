"""
ACR1281U-C1 NFC Card Reader (PC/SC)
"""
import asyncio
from typing import Optional, Callable, Dict
from ..config import MOCK_MODE


class CardReader:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self.reader = None
        self.connection = None
        self.on_card_read: Optional[Callable] = None
        self._running = False
    
    async def connect(self) -> bool:
        if self.mock_mode:
            return True
        
        try:
            from smartcard.System import readers
            from smartcard.CardMonitor import CardMonitor
            from smartcard.CardObserver import CardObserver
            
            available = readers()
            if not available:
                print("No card readers found")
                return False
            
            self.reader = available[0]
            return True
        except ImportError:
            print("pyscard not installed, switching to mock mode")
            self.mock_mode = True
            return True
        except Exception as e:
            print(f"Card reader error: {e}")
            return False
    
    async def start_monitoring(self):
        self._running = True
        if self.mock_mode:
            return
        
        asyncio.create_task(self._monitor_loop())
    
    async def _monitor_loop(self):
        while self._running:
            try:
                await asyncio.sleep(0.5)
            except:
                break
    
    def stop_monitoring(self):
        self._running = False
    
    async def read_card(self) -> Optional[Dict]:
        if self.mock_mode:
            return None
        
        try:
            connection = self.reader.createConnection()
            connection.connect()
            
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(GET_UID)
            
            if sw1 == 0x90 and sw2 == 0x00:
                uid = ''.join(format(x, '02X') for x in data)
                return {
                    'uid': uid,
                    'card_type': 'library',
                }
            
            connection.disconnect()
        except:
            pass
        
        return None
    
    def simulate_card(self, uid: str, card_type: str = 'library'):
        if self.on_card_read:
            self.on_card_read({
                'uid': uid,
                'card_type': card_type,
            })


card_reader = CardReader()
