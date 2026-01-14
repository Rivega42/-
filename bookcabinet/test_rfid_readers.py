#!/usr/bin/env python3
"""
Тест RFID считывателей с выводом UID карт
Показывает что считывают NFC и UHF в реальном времени
"""
import asyncio
import sys
import os
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bookcabinet.rfid.unified_card_reader import unified_reader
from bookcabinet.config import RFID

# Цвета для терминала
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color
BOLD = '\033[1m'


def print_header():
    """Печать заголовка"""
    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}   ТЕСТ RFID СЧИТЫВАТЕЛЕЙ - BookCabinet v2.1{NC}")
    print(f"{BOLD}{'='*60}{NC}")
    print()


def print_status(nfc_status: bool, uhf_status: bool):
    """Печать статуса подключения"""
    print(f"{BOLD}Статус подключения:{NC}")
    print(f"  {'✅' if nfc_status else '❌'} NFC (ACR1281U-C):  {GREEN if nfc_status else RED}{'Подключен' if nfc_status else 'Не найден'}{NC}")
    print(f"  {'✅' if uhf_status else '❌'} UHF (IQRFID-5102): {GREEN if uhf_status else RED}{'Подключен' if uhf_status else 'Не найден'}{NC}")
    print()


def format_uid(uid: str, source: str) -> str:
    """Форматирование UID для красивого вывода"""
    # Добавляем разделители для читаемости
    if len(uid) > 8:
        # Для длинных UHF меток - группируем по 4 символа
        formatted = ' '.join([uid[i:i+4] for i in range(0, len(uid), 4)])
    else:
        # Для коротких NFC - группируем по 2 символа
        formatted = ' '.join([uid[i:i+2] for i in range(0, len(uid), 2)])
    return formatted


# Счетчики для статистики
card_counts = {'nfc': 0, 'uhf': 0}
last_cards = {}


def on_card_detected(uid: str, source: str):
    """Callback при обнаружении карты с красивым выводом"""
    global card_counts, last_cards
    
    # Увеличиваем счетчик
    card_counts[source] += 1
    
    # Запоминаем последнюю карту
    last_cards[source] = uid
    
    # Время обнаружения
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    # Выбираем цвет в зависимости от источника
    if source == 'nfc':
        color = CYAN
        icon = '📇'
        reader_name = 'NFC/ACR1281'
        card_type = 'Билет библиотеки'
    else:
        color = MAGENTA
        icon = '💳'
        reader_name = 'UHF/IQRFID'
        card_type = 'ЕКП карта'
    
    # Форматированный вывод
    print(f"\n{BOLD}{color}{'='*50}{NC}")
    print(f"{icon} {BOLD}КАРТА ОБНАРУЖЕНА!{NC}")
    print(f"{BOLD}Время:{NC}      {timestamp}")
    print(f"{BOLD}Считыватель:{NC} {reader_name}")
    print(f"{BOLD}Тип карты:{NC}   {card_type}")
    print(f"{BOLD}UID:{NC}         {color}{format_uid(uid, source)}{NC}")
    print(f"{BOLD}Raw UID:{NC}     {uid}")
    print(f"{BOLD}Длина:{NC}       {len(uid)} символов")
    print(f"{BOLD}Счетчик:{NC}     {card_counts[source]} карт(а) от {source.upper()}")
    print(f"{color}{'='*50}{NC}\n")


async def test_readers():
    """Основная функция тестирования"""
    print_header()
    
    # Получаем конфигурацию из config.py
    uhf_port = RFID.get('uhf_card_reader', '/dev/rfid_uhf_card')
    print(f"{BOLD}Конфигурация:{NC}")
    print(f"  UHF порт: {YELLOW}{uhf_port}{NC}")
    print(f"  NFC: через PC/SC")
    print()
    
    # Конфигурируем reader
    unified_reader.configure(
        uhf_port=uhf_port,
        mock_mode=False  # Реальное железо
    )
    
    # Устанавливаем callback
    unified_reader.on_card_read = on_card_detected
    
    # Подключаемся к считывателям
    print(f"{YELLOW}Подключение к считывателям...{NC}")
    status = await unified_reader.connect()
    
    print_status(status['nfc'], status['uhf'])
    
    if not status['nfc'] and not status['uhf']:
        print(f"{RED}❌ Нет доступных считывателей!{NC}")
        print("\nПроверьте:")
        print("  1. Подключение USB кабелей")
        print("  2. Права доступа (группы dialout, plugdev)")
        print("  3. Установку драйверов (pcscd, pyscard)")
        return
    
    print(f"{GREEN}✅ Система готова к тестированию{NC}\n")
    print(f"{BOLD}Инструкции:{NC}")
    print("  • Поднесите карту к любому считывателю")
    print("  • NFC считыватель - для читательских билетов")
    print("  • UHF считыватель - для ЕКП карт")
    print(f"  • Нажмите {YELLOW}Ctrl+C{NC} для выхода")
    print()
    print(f"{CYAN}Ожидание карты...{NC}")
    print()
    
    try:
        # Запускаем опрос с интервалом 0.2 сек для быстрой реакции
        await unified_reader.start(poll_interval=0.2)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Остановка...{NC}")
    finally:
        # Выводим статистику
        print(f"\n{BOLD}{'='*50}{NC}")
        print(f"{BOLD}СТАТИСТИКА СЕССИИ:{NC}")
        print(f"  NFC карт считано: {GREEN}{card_counts['nfc']}{NC}")
        print(f"  UHF карт считано: {MAGENTA}{card_counts['uhf']}{NC}")
        
        if last_cards:
            print(f"\n{BOLD}Последние карты:{NC}")
            for source, uid in last_cards.items():
                print(f"  {source.upper()}: {format_uid(uid, source)}")
        
        print(f"{BOLD}{'='*50}{NC}\n")
        
        # Отключаемся
        unified_reader.disconnect()
        print(f"{GREEN}✓ Тест завершен{NC}\n")


async def increase_power():
    """Попытка увеличить мощность считывателей"""
    print(f"\n{YELLOW}Настройка мощности считывателей...{NC}")
    
    # Для IQRFID-5102 (UHF)
    try:
        from bookcabinet.hardware.iqrfid5102_driver import IQRFID5102
        
        uhf = IQRFID5102(RFID.get('uhf_card_reader', '/dev/rfid_uhf_card'))
        if uhf.connect():
            print(f"  {GREEN}✓{NC} Подключен к IQRFID-5102")
            
            # Команда установки максимальной мощности (30 dBm)
            # Протокол 0xA0, команда SetPower
            SET_POWER_CMD = bytes([0xA0, 0x05, 0x00, 0x01, 0x1E])  # 0x1E = 30 dBm
            checksum = (~sum(SET_POWER_CMD) + 1) & 0xFF
            command = SET_POWER_CMD + bytes([checksum])
            
            uhf.ser.write(command)
            response = uhf.ser.read(64)
            
            if response:
                print(f"  {GREEN}✓{NC} Мощность UHF установлена на максимум (30 dBm)")
            else:
                print(f"  {YELLOW}⚠{NC} Не удалось установить мощность UHF")
            
            uhf.disconnect()
    except Exception as e:
        print(f"  {RED}✗{NC} Ошибка настройки UHF: {e}")
    
    # Для ACR1281 (NFC) - обычно работает на максимальной мощности
    print(f"  {BLUE}ℹ{NC} NFC ACR1281 обычно работает на максимальной мощности")
    print()


if __name__ == "__main__":
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == '--power':
        # Сначала увеличиваем мощность
        asyncio.run(increase_power())
    
    # Запускаем тест
    try:
        asyncio.run(test_readers())
    except Exception as e:
        print(f"{RED}Ошибка: {e}{NC}")
        sys.exit(1)
