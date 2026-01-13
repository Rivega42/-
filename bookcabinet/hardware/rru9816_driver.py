# rru9816_driver.py
# Драйвер RRU9816 для Raspberry Pi
# Протокол реверснут через serial sniffer

import serial
import time
from typing import List, Optional

class RRU9816:
    """Драйвер для UHF RFID ридера RRU9816"""
    
    TIMEOUT = 1.0
    
    # Команды
    CMD_GET_INFO = 0x21
    CMD_INVENTORY = 0x01
    
    def __init__(self, port: str, baudrate: int = 57600, debug: bool = False):
        self.port = port
        self.baudrate = baudrate
        self.debug = debug
        self.serial: Optional[serial.Serial] = None
        self.address = 0x00
    
    def connect(self) -> bool:
        """Подключение к ридеру"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.baudrate,
                timeout=self.TIMEOUT
            )
            time.sleep(0.1)
            
            # Пробуем получить инфо
            info = self.get_info()
            if info:
                return True
            
            # Может другой baudrate?
            if self.baudrate != 115200:
                self.serial.baudrate = 115200
                self.baudrate = 115200
                if self.debug:
                    print(f"  Пробуем 115200...")
                info = self.get_info()
                if info:
                    return True
            
            return False
            
        except serial.SerialException as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение"""
        if self.serial:
            self.serial.close()
            self.serial = None
    
    def _crc16_ccitt(self, data: bytes) -> int:
        """CRC-16/CCITT-FALSE"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
                crc &= 0xFFFF
        return crc
    
    def _crc16_modbus(self, data: bytes) -> int:
        """CRC-16/MODBUS"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _send_raw(self, packet: bytes) -> Optional[bytes]:
        """Отправка сырого пакета (для тестирования известных команд)"""
        if not self.serial:
            return None
        
        if self.debug:
            print(f"  TX: {packet.hex(' ')}")
        
        self.serial.reset_input_buffer()
        self.serial.write(packet)
        time.sleep(0.1)
        
        # Читаем ответ
        len_byte = self.serial.read(1)
        if not len_byte:
            if self.debug:
                print(f"  RX: нет ответа")
            return None
        
        resp_len = len_byte[0]
        response = self.serial.read(resp_len)
        
        full_response = len_byte + response
        if self.debug:
            print(f"  RX: {full_response.hex(' ')}")
        
        return response
    
    def get_info(self) -> Optional[dict]:
        """Получить информацию о ридере (используем точную команду из снифера)"""
        # Точная команда из снифера: 04 ff 21 19 95
        packet = bytes([0x04, 0xff, 0x21, 0x19, 0x95])
        response = self._send_raw(packet)
        
        if not response or len(response) < 10:
            return None
        
        return {
            'address': response[0],
            'command': response[1],
            'version_major': response[3] if len(response) > 3 else 0,
            'version_minor': response[4] if len(response) > 4 else 0,
            'raw': response.hex(' ')
        }
    
    def inventory(self) -> List[str]:
        """Поиск меток (используем точную команду из снифера)"""
        tags = set()
        
        # Точная команда из снифера: 09 00 01 01 00 00 80 0a 76 fc
        packet = bytes([0x09, 0x00, 0x01, 0x01, 0x00, 0x00, 0x80, 0x0a, 0x76, 0xfc])
        
        for _ in range(10):  # несколько попыток
            response = self._send_raw(packet)
            
            if response and len(response) > 6:
                # [addr] [cmd] [???] [status] [count] [epc_len] [epc...] [crc]
                status = response[3] if len(response) > 3 else 0
                count = response[4] if len(response) > 4 else 0
                
                if status == 0x01 and count > 0:
                    epc_len = response[5]
                    if len(response) >= 6 + epc_len:
                        epc_bytes = response[6:6+epc_len]
                        epc = epc_bytes.hex().upper()
                        tags.add(epc)
        
        return list(tags)
    
    def inventory_continuous(self, duration: float = 2.0) -> List[str]:
        """Непрерывный поиск меток"""
        tags = set()
        start = time.time()
        
        packet = bytes([0x09, 0x00, 0x01, 0x01, 0x00, 0x00, 0x80, 0x0a, 0x76, 0xfc])
        
        while time.time() - start < duration:
            response = self._send_raw(packet)
            
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


if __name__ == "__main__":
    import sys
    
    # Порт
    if sys.platform == 'win32':
        port = "COM2"
    else:
        port = "/dev/ttyUSB0"
    
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    print(f"=== Тест RRU9816 на {port} ===")
    
    reader = RRU9816(port, baudrate=57600, debug=True)
    
    if reader.connect():
        print(f"✓ Подключено! (baudrate={reader.baudrate})")
        
        info = reader.get_info()
        if info:
            print(f"✓ Версия: {info.get('version_major')}.{info.get('version_minor')}")
        
        print("\nСканирование меток (2 сек)...")
        tags = reader.inventory_continuous(2.0)
        
        if tags:
            print(f"\n✓ Найдено меток: {len(tags)}")
            for tag in tags:
                print(f"  EPC: {tag}")
        else:
            print("  Меток не найдено (поднеси метку к ридеру)")
        
        reader.disconnect()
    else:
        print("✗ Не удалось подключиться")
        print("  Проверь что порт не занят другой программой")
