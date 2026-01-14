# iqrfid5102_driver.py
# Драйвер IQRFID-5102 для Raspberry Pi
#
# Протокол: [LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]
# CRC-16: polynomial 0x8408, init 0xFFFF
# Baudrate: 57600
#
# Использование:
#   from iqrfid5102_driver import IQRFID5102
#   reader = IQRFID5102('/dev/ttyUSB0')  # или 'COM2' на Windows
#   reader.connect()
#   tags = reader.inventory()
#   for tag in tags:
#       print(tag)
#   reader.disconnect()

import serial
import time
from typing import List, Optional

class IQRFID5102:
    """Драйвер для UHF RFID ридера IQRFID-5102"""
    
    BAUDRATE = 57600
    TIMEOUT = 1.0
    
    # Команды
    CMD_INVENTORY = 0x01
    CMD_SET_POWER = 0x07  # Команда установки мощности (предположительно)
    CMD_GET_POWER = 0x08  # Команда получения текущей мощности
    CMD_SET_PARAM = 0x09  # Установка параметров
    
    # Статусы
    STATUS_NO_TAGS = 0xFB
    STATUS_TAG_FOUND = 0x01
    STATUS_OK = 0x00
    
    def __init__(self, port: str, debug: bool = False):
        self.port = port
        self.debug = debug
        self.serial: Optional[serial.Serial] = None
        self.address = 0x00
    
    def connect(self) -> bool:
        """Подключение к ридеру"""
        try:
            self.serial = serial.Serial(
                self.port,
                self.BAUDRATE,
                timeout=self.TIMEOUT
            )
            time.sleep(0.1)
            
            # Проверяем связь - отправляем Inventory
            self.serial.reset_input_buffer()
            cmd = self._build_cmd(self.CMD_INVENTORY)
            self.serial.write(cmd)
            time.sleep(0.1)
            response = self.serial.read(64)
            
            # Если есть ответ - ридер работает
            if response and len(response) >= 5:
                if self.debug:
                    print(f"  Ридер ответил: {response.hex(' ')}")
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
    
    def _crc16(self, data: bytes) -> bytes:
        """CRC-16 с полиномом 0x8408"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    
    def _build_cmd(self, cmd: int, data: bytes = b'') -> bytes:
        """
        Формат: [LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]
        LEN = addr + cmd + data + 2 (crc)
        """
        length = 1 + 1 + len(data) + 2
        packet = bytes([length, self.address, cmd]) + data
        crc = self._crc16(packet)
        packet += crc
        return packet
    
    def _send_command(self, cmd: int, data: bytes = b'') -> Optional[bytes]:
        """Отправка команды и получение ответа"""
        if not self.serial:
            return None
        
        packet = self._build_cmd(cmd, data)
        
        if self.debug:
            print(f"  TX: {packet.hex(' ')}")
        
        self.serial.reset_input_buffer()
        self.serial.write(packet)
        time.sleep(0.1)
        
        response = self.serial.read(64)
        
        if self.debug:
            if response:
                print(f"  RX: {response.hex(' ')}")
            else:
                print(f"  RX: нет ответа")
        
        return response if response else None
    
    def set_power(self, power_dbm: int = 30) -> bool:
        """
        Установка мощности передатчика
        
        Args:
            power_dbm: Мощность в dBm (5-30)
            
        Returns:
            True если успешно
        """
        # Ограничиваем диапазон
        power_dbm = max(5, min(30, power_dbm))
        
        # Пробуем разные варианты команд
        commands = [
            (self.CMD_SET_POWER, bytes([power_dbm])),
            (self.CMD_SET_PARAM, bytes([0x02, power_dbm])),  # 0x02 - параметр мощности
            (0x06, bytes([power_dbm])),  # Альтернативная команда
        ]
        
        for cmd, data in commands:
            response = self._send_command(cmd, data)
            
            if response and len(response) >= 4:
                status = response[3] if len(response) > 3 else None
                if status == self.STATUS_OK or status == 0x01:
                    if self.debug:
                        print(f"  ✓ Мощность установлена: {power_dbm} dBm")
                    return True
        
        return False
    
    def get_power(self) -> Optional[int]:
        """
        Получение текущей мощности
        
        Returns:
            Мощность в dBm или None
        """
        response = self._send_command(self.CMD_GET_POWER)
        
        if response and len(response) >= 5:
            power = response[4]
            if self.debug:
                print(f"  Текущая мощность: {power} dBm")
            return power
        
        return None
    
    def inventory(self, rounds: int = 1) -> List[str]:
        """
        Поиск меток
        
        Returns:
            Список EPC меток (hex строки)
        """
        tags = set()
        
        for _ in range(rounds):
            response = self._send_command(self.CMD_INVENTORY)
            
            if not response or len(response) < 5:
                continue
            
            # Парсим ответ
            # [LEN] [ADR] [CMD] [STATUS/COUNT] [COUNT] [EPC_LEN] [EPC...] [CRC]
            status = response[3]
            
            if status == self.STATUS_TAG_FOUND and len(response) > 6:
                count = response[4]
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
        
        while time.time() - start < duration:
            response = self._send_command(self.CMD_INVENTORY)
            
            if response and len(response) > 6:
                status = response[3]
                
                if status == self.STATUS_TAG_FOUND:
                    epc_len = response[5]
                    if len(response) >= 6 + epc_len:
                        epc_bytes = response[6:6+epc_len]
                        epc = epc_bytes.hex().upper()
                        tags.add(epc)
            
            time.sleep(0.05)
        
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
    
    print(f"=== Тест IQRFID-5102 на {port} ===")
    
    reader = IQRFID5102(port, debug=True)
    
    if reader.connect():
        print("✓ Подключено!")
        
        # Пробуем установить максимальную мощность
        print("\nПробуем установить мощность 30 dBm...")
        if reader.set_power(30):
            print("✓ Мощность установлена!")
        else:
            print("✗ Не удалось установить мощность")
        
        # Пробуем получить текущую мощность
        power = reader.get_power()
        if power:
            print(f"Текущая мощность: {power} dBm")
        
        print("\nСканирование меток (3 сек)...")
        print("Поднеси метку к ридеру!")
        tags = reader.inventory_continuous(3.0)
        
        if tags:
            print(f"\n✓ Найдено меток: {len(tags)}")
            for tag in tags:
                print(f"  EPC: {tag}")
        else:
            print("\n  Меток не найдено")
        
        reader.disconnect()
    else:
        print("✗ Не удалось подключиться")
        print("  Проверь что порт не занят другой программой")
