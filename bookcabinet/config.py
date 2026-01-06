"""
Конфигурация системы BookCabinet
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

# GPIO пины (Raspberry Pi)
GPIO_PINS = {
    'MOTOR_A_STEP': 18,
    'MOTOR_A_DIR': 27,
    'MOTOR_B_STEP': 23,
    'MOTOR_B_DIR': 22,
    'TRAY_STEP': 24,
    'TRAY_DIR': 25,
    'SERVO_LOCK_1': 12,
    'SERVO_LOCK_2': 13,
    'SHUTTER_OUTER': 4,
    'SHUTTER_INNER': 5,
    'SENSOR_X_BEGIN': 16,
    'SENSOR_X_END': 20,
    'SENSOR_Y_BEGIN': 21,
    'SENSOR_Y_END': 26,
    'SENSOR_TRAY_BEGIN': 19,
    'SENSOR_TRAY_END': 6,
}

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

# Заблокированные ячейки
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

# Telegram
TELEGRAM = {
    'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),
    'enabled': os.environ.get('TELEGRAM_ENABLED', 'false').lower() == 'true',
}

# Логирование
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'bookcabinet/logs/system.log')
