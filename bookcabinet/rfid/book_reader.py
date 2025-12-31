"""
IQRFID-5102 UHF Book Reader (Serial)
"""
import asyncio
from typing import Optional, List, Callable
from ..config import MOCK_MODE, RFID


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
    return crc


class BookReader:
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self.serial = None
        self.port = RFID['book_reader']
        self.baudrate = RFID['book_baudrate']
        self.on_tag_read: Optional[Callable] = None
        self._running = False
    
    async def connect(self) -> bool:
        if self.mock_mode:
            return True
        
        try:
            import serial
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=0.5
            )
            return True
        except ImportError:
            print("pyserial not installed, switching to mock mode")
            self.mock_mode = True
            return True
        except Exception as e:
            print(f"Book reader error: {e}")
            return False
    
    def disconnect(self):
        if self.serial:
            self.serial.close()
            self.serial = None
    
    async def inventory(self) -> List[str]:
        if self.mock_mode:
            return []
        
        try:
            cmd = bytes([0x04, 0x00, 0x01])
            crc = crc16(cmd)
            packet = cmd + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
            
            self.serial.write(packet)
            await asyncio.sleep(0.1)
            
            response = self.serial.read(256)
            tags = self._parse_inventory(response)
            return tags
        except Exception as e:
            print(f"Inventory error: {e}")
            return []
    
    def _parse_inventory(self, data: bytes) -> List[str]:
        tags = []
        if len(data) < 5:
            return tags
        
        return tags
    
    async def start_polling(self, interval: float = 1.0):
        self._running = True
        while self._running:
            tags = await self.inventory()
            for tag in tags:
                if self.on_tag_read:
                    self.on_tag_read({'epc': tag})
            await asyncio.sleep(interval)
    
    def stop_polling(self):
        self._running = False
    
    def simulate_tag(self, epc: str):
        if self.on_tag_read:
            self.on_tag_read({'epc': epc})


book_reader = BookReader()
