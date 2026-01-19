"""
Конфигурация системы BookCabinet

GPIO пины настроены для GPIO Expansion Board с пружинными клеммниками
Схема подключения: RPI3_WIRING_FINAL.md v3.0

ВНИМАНИЕ: Реальная распиновка найдена сканированием 2025-01-19!
"""
import os

# Режим работы
MOCK_MODE = os.environ.get('MOCK_MODE', 'true').lower() == 'true'
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

# Сервер
HOST = os.environ.get('HOST', '0.0.0.0')
PORT = int(os.environ.get('PORT', 5000))

# База данных
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'bookcabinet/shelf_data.db')

# =============================================================================
# GPIO пины (Raspberry Pi + GPIO Expansion Board)
# РЕАЛЬНАЯ РАСПИНОВКА — найдено сканированием 2025-01-19
# =============================================================================
GPIO_PINS = {
    # Моторы XY (CoreXY)
    'MOTOR_A_STEP': 2,      # Работает ✓
    'MOTOR_A_DIR': 3,       # Работает ✓
    'MOTOR_B_STEP': 19,     # Работает ✓
    'MOTOR_B_DIR': 21,      # Работает ✓
    
    # Мотор Tray — РЕАЛЬНОЕ подключение!
    'TRAY_STEP': 18,        # Было 24, реально 18
    'TRAY_DIR': 27,         # Было 25, реально 27
    
    # Сервоприводы замков
    'SERVO_LOCK_1': 12,     # Передний замок (найдено сканированием)
    'SERVO_LOCK_2': 13,     # Задний замок — TODO: проверить!
    
    # Шторки (реле)
    'SHUTTER_OUTER': 14,    # Внешняя
    'SHUTTER_INNER': 15,    # Внутренняя
    
    # Датчики концевиков — РЕАЛЬНОЕ подключение! HIGH = сработал
    'SENSOR_X_BEGIN': 9,    # Левый (было 10)
    'SENSOR_X_END': 10,     # Правый (было 9)
    'SENSOR_Y_BEGIN': 8,    # Нижний (было 11)
    'SENSOR_Y_END': 11,     # Верхний (было 8)
    'SENSOR_TRAY_BEGIN': 7, # Платформа назад
    'SENSOR_TRAY_END': 20,  # Платформа вперёд
}

# Логика датчиков: HIGH = сработал (не LOW!)
SENSOR_ACTIVE_HIGH = True

# Использовать встроенную подтяжку RPi для датчиков (резисторы 10K не нужны!)
SENSOR_USE_PULLUP = True

# Параметры моторов
MOTOR_SPEEDS = {
    'xy': 4000,             # шагов/сек для CoreXY
    'tray': 2000,           # шагов/сек для Tray
    'acceleration': 8000,
}

# Рассчитанные задержки для Python GPIO (микросекунды между HIGH/LOW)
# Формула: delay = 1 / (2 * speed)
MOTOR_DELAYS = {
    'xy': 0.000125,         # 4000 шагов/сек → 125мкс
    'tray': 0.00025,        # 2000 шагов/сек → 250мкс
}

# Параметры сервоприводов
SERVO_ANGLES = {
    'lock1_open': 0,
    'lock1_close': 95,
    'lock2_open': 0,
    'lock2_close': 95,
}

# Шкаф
CABINET = {
    'rows': ['FRONT', 'BACK'],
    'columns': 3,
    'positions': 21,
    'total_cells': 126,
    'window': {'row': 'FRONT', 'x': 1, 'y': 9},
}

# Заблокированные ячейки (механизм, окно выдачи)
BLOCKED_CELLS = {
    'FRONT': [
        {'x': 1, 'y': 7}, {'x': 1, 'y': 8}, {'x': 1, 'y': 9}, {'x': 1, 'y': 10},
        {'x': 1, 'y': 11}, {'x': 1, 'y': 12}, {'x': 1, 'y': 13}, {'x': 1, 'y': 14},
        {'x': 1, 'y': 15}, {'x': 1, 'y': 16}, {'x': 1, 'y': 17}, {'x': 1, 'y': 18},
    ],
    'BACK': [
        {'x': 0, 'y': 19}, {'x': 0, 'y': 20},
        {'x': 1, 'y': 19}, {'x': 1, 'y': 20},
        {'x': 2, 'y': 20},
    ],
}

# Таймауты операций (мс)
TIMEOUTS = {
    'move': 1500,
    'tray_extend': 800,
    'tray_retract': 800,
    'cell_open': 1000,
    'cell_close': 1000,
    'user_wait': 30000,
}

# =============================================================================
# RFID - Считыватели
# =============================================================================
RFID = {
    # Внешняя панель - считыватели карт пользователей
    'nfc_card_reader': '/dev/pcsc',           # ACR1281U-C (NFC, PC/SC)
    'uhf_card_reader': '/dev/rfid_uhf_card',  # IQRFID-5102 (UHF, Serial)
    'uhf_card_baudrate': 57600,
    
    # Внутри шкафа - считыватель книг
    'book_reader': '/dev/rfid_book',          # RRU9816 (UHF, Serial)
    'book_baudrate': 57600,
    
    # Fallback на прямые порты
    'uhf_card_reader_fallback': '/dev/ttyUSB0',
    'book_reader_fallback': '/dev/ttyUSB1',
    
    # Параметры опроса карт
    'card_poll_interval': 0.3,
    'card_debounce_ms': 800,
    'uhf_card_uid_length': 24,
}

# =============================================================================
# IRBIS64 — Библиотечная система
# =============================================================================
IRBIS = {
    'host': os.environ.get('IRBIS_HOST', '172.29.67.70'),
    'port': int(os.environ.get('IRBIS_PORT', 6666)),
    'username': os.environ.get('IRBIS_USERNAME', '09f00st'),
    'password': os.environ.get('IRBIS_PASSWORD', 'f00st'),
    'database': os.environ.get('IRBIS_DATABASE', 'KAT%SERV09%'),
    'readers_database': os.environ.get('IRBIS_READERS_DB', 'RDR'),
    'loan_days': int(os.environ.get('IRBIS_LOAN_DAYS', 30)),
    'location_code': os.environ.get('IRBIS_LOCATION_CODE', '09'),
    'mock': os.environ.get('IRBIS_MOCK', 'false').lower() == 'true',
}

# Wi-Fi AP (для Raspberry Pi)
WIFI_AP = {
    'ssid': 'BookCabinet',
    'password': 'BookCabinet123',
    'ip': '192.168.4.1',
}

# Telegram уведомления
TELEGRAM = {
    'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
    'enabled': os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true',
}

# Логирование
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'bookcabinet/logs/system.log')
