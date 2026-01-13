# rru9816_driver.py
# Драйвер RRU9816 для Raspberry Pi
# Протокол реверснут через serial sniffer
#
# Использование:
#   from rru9816_driver import RRU9816
#   reader = RRU9816('/dev/ttyUSB0')  # или 'COM2' на Windows
#   reader.connect()
#   tags = reader.inventory()
#   for tag in tags:
#       print(tag)
#   reader.disconnect()

import serial
import struct
import time
from typing import List, Optional

class RRU9816:
    """Драйвер для UHF RFID ридера RRU9816"""
    
    BAUDRATE = 57600
    TIMEOUT = 1.0
    
    # Команды
    CMD_GET_INFO = 0x21
    CMD_INVENTORY = 0x01
    
    def __init__(self, port: str):
        self.port = port
        self.serial: Optional[serial.Serial] = None
        self.address = 0x00  # адрес ридера
    
    def connect(self) -> bool:
        """Подключение к ридеру"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.BAUDRATE,
                timeout=self.TIMEOUT
            )
            time.sleep(0.1)
            # Проверяем связь
            info = self.get_info()
            return info is not None
        except serial.SerialException as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение"""
        if self.serial:
            self.serial.close()
            self.serial = None
    
    def _crc16(self, data: bytes) -> bytes:
        """CRC-16/CCITT-FALSE (poly=0x1021, init=0xFFFF)"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return struct.pack('<H', crc)  # little-endian
    
    def _send_command(self, cmd: int, data: bytes = b'', addr: int = None) -> Optional[bytes]:
        """Отправка команды и получение ответа"""
        if not self.serial:
            return None
        
        if addr is None:
            addr = self.address
        
        # Формируем пакет: [len] [addr] [cmd] [data] [crc16]
        payload = bytes([addr, cmd]) + data
        length = len(payload) + 2  # +2 для CRC
        packet = bytes([length]) + payload
        crc = self._crc16(packet)
        packet += crc
        
        # Отправляем
        self.serial.reset_input_buffer()
        self.serial.write(packet)
        
        # Читаем ответ
        time.sleep(0.05)
        
        # Первый байт - длина
        len_byte = self.serial.read(1)
        if not len_byte:
            return None
        
        resp_len = len_byte[0]
        response = self.serial.read(resp_len)
        
        if len(response) < resp_len:
            return None
        
        return response
    
    def get_info(self) -> Optional[dict]:
        """Получить информацию о ридере"""
        response = self._send_command(self.CMD_GET_INFO, addr=0xFF)
        
        if not response or len(response) < 10:
            return None
        
        # Парсим ответ
        # 00 21 00 03 01 10 02 4e 00 07 0a 01 01 00 00 [crc]
        return {
            'address': response[0],
            'command': response[1],
            'version_major': response[3],
            'version_minor': response[4],
            'power': response[7],
            'raw': response.hex(' ')
        }
    
    def inventory(self, rounds: int = 1) -> List[str]:
        """
        Поиск меток
        
        Returns:
            Список EPC меток (hex строки)
        """
        tags = set()  # используем set для дедупликации
        
        # Данные команды Inventory (из снифера)
        # 01 01 00 00 80 0a
        inv_data = bytes([0x01, 0x00, 0x00, 0x80, 0x0a])
        
        for _ in range(rounds):
            response = self._send_command(self.CMD_INVENTORY, inv_data)
            
            if not response or len(response) < 5:
                continue
            
            # Парсим ответ
            # [addr] [cmd] [???] [status] [count] [epc_len] [epc...] [crc]
            # 00     01    01    01       01      0c        [12 bytes EPC] [crc]
            
            status = response[3] if len(response) > 3 else 0
            count = response[4] if len(response) > 4 else 0
            
            if status == 0x01 and count > 0 and len(response) > 6:
                epc_len = response[5]
                if len(response) >= 6 + epc_len:
                    epc_bytes = response[6:6+epc_len]
                    epc = epc_bytes.hex().upper()
                    tags.add(epc)
        
        return list(tags)
    
    def inventory_continuous(self, duration: float = 2.0) -> List[str]:
        """
        Непрерывный поиск меток в течение указанного времени
        
        Args:
            duration: время сканирования в секундах
            
        Returns:
            Список уникальных EPC меток
        """
        tags = set()
        start = time.time()
        
        inv_data = bytes([0x01, 0x00, 0x00, 0x80, 0x0a])
        
        while time.time() - start < duration:
            response = self._send_command(self.CMD_INVENTORY, inv_data)
            
            if response and len(response) > 6:
                status = response[3]
                count = response[4]
                
                if status == 0x01 and count > 0:
                    epc_len = response[5]
                    if len(response) >= 6 + epc_len:
                        epc_bytes = response[6:6+epc_len]
                        epc = epc_bytes.hex().upper()
                        tags.add(epc)
        
        return list(tags)


# Тест
if __name__ == "__main__":
    import sys
    
    # Определяем порт
    if sys.platform == 'win32':
        port = "COM2"
    else:
        port = "/dev/ttyUSB0"
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    print(f"=== Тест RRU9816 на {port} ===")
    
    reader = RRU9816(port)
    
    if reader.connect():
        print("✓ Подключено!")
        
        info = reader.get_info()
        if info:
            print(f"✓ Ридер: версия {info.get('version_major')}.{info.get('version_minor')}")
        
        print("\nСканирование меток (2 сек)...")
        tags = reader.inventory_continuous(2.0)
        
        if tags:
            print(f"✓ Найдено меток: {len(tags)}")
            for tag in tags:
                print(f"  EPC: {tag}")
        else:
            print("  Меток не найдено")
        
        reader.disconnect()
    else:
        print("✗ Не удалось подключиться")
