"""
Конфигурация системы BookCabinet

GPIO пины настроены для GPIO Expansion Board с пружинными клеммниками
Схема подключения: RPI3_WIRING_FINAL.md v3.0
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
# Схема: RPI3_WIRING_FINAL.md v3.0
# =============================================================================
GPIO_PINS = {
    # Моторы XY (CoreXY) — Блок A
    'MOTOR_A_STEP': 2,      # Клемма 2 (SDA1)
    'MOTOR_A_DIR': 3,       # Клемма 3 (SCL1)
    
    # Мотор B — Блок C
    'MOTOR_B_STEP': 19,     # Клемма L (PCMfs)
    'MOTOR_B_DIR': 21,      # Клемма N (PCMo)
    
    # Мотор Tray — Штыревой разъём
    'TRAY_STEP': 24,        # Pin 18 (GPIO24)
    'TRAY_DIR': 25,         # Pin 22 (GPIO25)
    
    # Сервоприводы замков — Блок C (PWM)
    'SERVO_LOCK_1': 18,     # Клемма J (PWM0) — передний замок
    'SERVO_LOCK_2': 13,     # Клемма K (PWM1) — задний замок
    
    # Шторки (реле) — Блок A
    'SHUTTER_OUTER': 14,    # Клемма 7 (TX0) — внешняя
    'SHUTTER_INNER': 15,    # Клемма 6 (RX0) — внутренняя
    
    # Датчики концевиков — Блок B (SPI пины)
    'SENSOR_X_BEGIN': 10,   # Клемма B (MOSI) — левый
    'SENSOR_X_END': 9,      # Клемма C (MISO) — правый
    'SENSOR_Y_BEGIN': 11,   # Клемма D (SCLK) — нижний
    'SENSOR_Y_END': 8,      # Клемма E (CE0) — верхний
    'SENSOR_TRAY_BEGIN': 7, # Клемма F (CE1) — платформа назад
    'SENSOR_TRAY_END': 20,  # Клемма M (PCMi) — платформа вперёд
}

# Использовать встроенную подтяжку RPi для датчиков (резисторы 10K не нужны!)
SENSOR_USE_PULLUP = True

# Параметры моторов
MOTOR_SPEEDS = {
    'xy': 4000,
    'tray': 2000,
    'acceleration': 8000,
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

# RFID
RFID = {
    'card_reader': '/dev/pcsc',
    'book_reader': '/dev/rfid_book',
    'book_baudrate': 57600,
}

# IRBIS64
IRBIS = {
    'host': os.environ.get('IRBIS_HOST', '192.168.1.100'),
    'port': int(os.environ.get('IRBIS_PORT', 6666)),
    'username': os.environ.get('IRBIS_USERNAME', 'MASTER'),
    'password': os.environ.get('IRBIS_PASSWORD', 'MASTERKEY'),
    'database': os.environ.get('IRBIS_DATABASE', 'IBIS'),
    'readers_database': os.environ.get('IRBIS_READERS_DB', 'RDR'),
    'loan_days': int(os.environ.get('IRBIS_LOAN_DAYS', 30)),
    'location_code': os.environ.get('IRBIS_LOCATION_CODE', '09'),
    'mock': os.environ.get('IRBIS_MOCK', 'true').lower() == 'true',
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
