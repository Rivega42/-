#!/usr/bin/env python3
"""
Настройка мощности RFID считывателей
Увеличивает дальность считывания карт
"""
import sys
import os
import time
import serial

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bookcabinet.config import RFID

# Цвета
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'
BOLD = '\033[1m'


def configure_iqrfid5102_power(port: str, power_dbm: int = 30):
    """
    Настройка мощности IQRFID-5102 (UHF)
    
    Args:
        port: Порт устройства
        power_dbm: Мощность в dBm (5-30, по умолчанию 30 - максимум)
    """
    print(f"\n{BOLD}Настройка IQRFID-5102 (UHF карты):{NC}")
    print(f"  Порт: {port}")
    print(f"  Целевая мощность: {power_dbm} dBm")
    
    try:
        # Открываем порт
        ser = serial.Serial(
            port=port,
            baudrate=57600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        
        print(f"  {GREEN}✓{NC} Порт открыт")
        
        # Команды протокола 0xA0 для IQRFID-5102
        # Формат: [Header, Len, Addr, Cmd, Data..., Checksum]
        
        # 1. Получаем текущую мощность
        GET_POWER = bytes([0xA0, 0x04, 0x00, 0x02])  # GetReaderParam
        checksum = (~sum(GET_POWER) + 1) & 0xFF
        command = GET_POWER + bytes([checksum])
        
        ser.write(command)
        time.sleep(0.1)
        response = ser.read(64)
        
        if response and len(response) >= 7:
            current_power = response[5] if len(response) > 5 else 0
            print(f"  Текущая мощность: {current_power} dBm")
        
        # 2. Устанавливаем новую мощность
        # Команда SetReaderParam (0x01)
        # Параметр 0x02 = RF Power
        SET_POWER = bytes([
            0xA0,  # Header
            0x06,  # Length
            0x00,  # Addr
            0x01,  # SetReaderParam
            0x02,  # Param: RF Power
            power_dbm & 0xFF  # Value
        ])
        checksum = (~sum(SET_POWER) + 1) & 0xFF
        command = SET_POWER + bytes([checksum])
        
        ser.write(command)
        time.sleep(0.1)
        response = ser.read(64)
        
        if response and response[3] == 0x01:  # Проверяем статус
            print(f"  {GREEN}✓{NC} Мощность установлена на {power_dbm} dBm")
        else:
            print(f"  {YELLOW}⚠{NC} Не удалось подтвердить установку мощности")
        
        # 3. Настраиваем другие параметры для лучшего считывания
        # Увеличиваем количество попыток инвентаризации
        SET_ROUNDS = bytes([
            0xA0,  # Header
            0x06,  # Length
            0x00,  # Addr
            0x01,  # SetReaderParam
            0x08,  # Param: Inventory rounds
            0x05   # Value: 5 rounds
        ])
        checksum = (~sum(SET_ROUNDS) + 1) & 0xFF
        command = SET_ROUNDS + bytes([checksum])
        
        ser.write(command)
        time.sleep(0.1)
        
        print(f"  {GREEN}✓{NC} Количество попыток чтения: 5")
        
        # 4. Настраиваем Q-параметр (влияет на скорость чтения)
        SET_Q = bytes([
            0xA0,  # Header
            0x06,  # Length
            0x00,  # Addr
            0x01,  # SetReaderParam
            0x09,  # Param: Q value
            0x04   # Value: Q=4
        ])
        checksum = (~sum(SET_Q) + 1) & 0xFF
        command = SET_Q + bytes([checksum])
        
        ser.write(command)
        time.sleep(0.1)
        
        print(f"  {GREEN}✓{NC} Q-параметр: 4 (оптимально для 1-15 меток)")
        
        ser.close()
        print(f"  {GREEN}✓{NC} Настройка завершена")
        return True
        
    except serial.SerialException as e:
        print(f"  {RED}✗{NC} Ошибка порта: {e}")
        return False
    except Exception as e:
        print(f"  {RED}✗{NC} Ошибка: {e}")
        return False


def configure_rru9816_power(port: str):
    """
    Настройка мощности RRU9816 (UHF книги)
    
    RRU9816 использует другой протокол, но попробуем стандартные команды
    """
    print(f"\n{BOLD}Настройка RRU9816 (книжные метки):{NC}")
    print(f"  Порт: {port}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=57600,
            timeout=1
        )
        
        print(f"  {GREEN}✓{NC} Порт открыт")
        
        # Для RRU9816 команды могут отличаться
        # Попробуем стандартную команду установки мощности
        # Обычно это команда 0xC5 или 0xC6
        
        # Попытка 1: Команда как у Impinj
        SET_POWER = bytes([0xBB, 0x00, 0xB6, 0x00, 0x02, 0x0A, 0xC8, 0x7E])
        ser.write(SET_POWER)
        time.sleep(0.1)
        response = ser.read(64)
        
        if response:
            print(f"  {YELLOW}ℹ{NC} Получен ответ: {response.hex()}")
        
        ser.close()
        print(f"  {BLUE}ℹ{NC} RRU9816 требует специфичный протокол")
        print(f"  {BLUE}ℹ{NC} Обычно работает на максимальной мощности по умолчанию")
        
    except Exception as e:
        print(f"  {YELLOW}⚠{NC} Не удалось настроить: {e}")


def configure_acr1281_range():
    """
    Информация о ACR1281 (NFC)
    
    ACR1281 обычно имеет фиксированную мощность и дальность ~10см
    """
    print(f"\n{BOLD}ACR1281U-C (NFC читательские билеты):{NC}")
    print(f"  {BLUE}ℹ{NC} Мощность: фиксированная (класс ISO 14443)")
    print(f"  {BLUE}ℹ{NC} Дальность: 5-10 см (стандарт NFC)")
    print(f"  {BLUE}ℹ{NC} Для увеличения дальности:")
    print(f"     • Убедитесь что карта параллельна считывателю")
    print(f"     • Избегайте металлических поверхностей рядом")
    print(f"     • Проверьте качество антенны в карте")


def test_reading_distance(port: str):
    """
    Тест дальности считывания после настройки
    """
    print(f"\n{BOLD}Тест дальности считывания:{NC}")
    print(f"  Порт: {port}")
    
    try:
        from bookcabinet.hardware.iqrfid5102_driver import IQRFID5102
        
        reader = IQRFID5102(port, debug=False)
        if not reader.connect():
            print(f"  {RED}✗{NC} Не удалось подключиться")
            return
        
        print(f"  {GREEN}✓{NC} Подключен к считывателю")
        print(f"\n  Поднесите карту на разном расстоянии...")
        print(f"  Нажмите Ctrl+C для выхода\n")
        
        last_read_time = 0
        max_reads_per_sec = 0
        
        try:
            while True:
                tags = reader.inventory(rounds=1)
                
                if tags:
                    current_time = time.time()
                    
                    # Считаем скорость чтения
                    if current_time - last_read_time < 1:
                        max_reads_per_sec += 1
                    else:
                        if max_reads_per_sec > 0:
                            print(f"  Скорость: {max_reads_per_sec} чтений/сек")
                        max_reads_per_sec = 1
                        last_read_time = current_time
                    
                    for tag in tags:
                        print(f"  {GREEN}✓{NC} Обнаружена: {tag}")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n  {YELLOW}Тест остановлен{NC}")
        
        reader.disconnect()
        
    except Exception as e:
        print(f"  {RED}✗{NC} Ошибка теста: {e}")


def main():
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}   НАСТРОЙКА МОЩНОСТИ RFID СЧИТЫВАТЕЛЕЙ{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    
    # Получаем порты из конфигурации
    uhf_card_port = RFID.get('uhf_card_reader', '/dev/rfid_uhf_card')
    book_port = RFID.get('book_reader', '/dev/rfid_book')
    
    # Проверяем существование портов
    if not os.path.exists(uhf_card_port):
        # Пробуем fallback
        uhf_card_port = RFID.get('uhf_card_reader_fallback', '/dev/ttyUSB0')
    
    if not os.path.exists(book_port):
        # Пробуем fallback
        book_port = RFID.get('book_reader_fallback', '/dev/ttyUSB1')
    
    print(f"\nКонфигурация:")
    print(f"  UHF карты (IQRFID-5102): {YELLOW}{uhf_card_port}{NC}")
    print(f"  UHF книги (RRU9816):      {YELLOW}{book_port}{NC}")
    
    # Меню выбора
    print(f"\n{BOLD}Выберите действие:{NC}")
    print("  1. Настроить все считыватели на максимальную мощность")
    print("  2. Настроить только IQRFID-5102 (карты)")
    print("  3. Настроить только RRU9816 (книги)")
    print("  4. Тест дальности IQRFID-5102")
    print("  5. Информация о настройках")
    print("  0. Выход")
    
    try:
        choice = input(f"\nВыбор: ")
        
        if choice == '1':
            configure_acr1281_range()
            configure_iqrfid5102_power(uhf_card_port, 30)
            configure_rru9816_power(book_port)
        elif choice == '2':
            power = input("Мощность в dBm (5-30, Enter для 30): ").strip()
            power = int(power) if power else 30
            power = max(5, min(30, power))  # Ограничиваем диапазон
            configure_iqrfid5102_power(uhf_card_port, power)
        elif choice == '3':
            configure_rru9816_power(book_port)
        elif choice == '4':
            test_reading_distance(uhf_card_port)
        elif choice == '5':
            configure_acr1281_range()
            print(f"\n{BOLD}Рекомендуемые настройки мощности:{NC}")
            print(f"  • IQRFID-5102: 25-30 dBm для максимальной дальности")
            print(f"  • RRU9816: обычно фиксированная на ~26 dBm")
            print(f"  • ACR1281: фиксированная ~13.56 MHz Class 1")
        
        print(f"\n{BOLD}{'='*60}{NC}")
        print(f"{GREEN}✓ Готово{NC}")
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Отменено{NC}")
    except Exception as e:
        print(f"\n{RED}Ошибка: {e}{NC}")


if __name__ == "__main__":
    main()
