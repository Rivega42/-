# BookCabinet GPIO Config — полная карта (10.03.2026)

GPIO_PINS = {
    # CoreXY моторы
    'MOTOR_A_STEP': 14,
    'MOTOR_A_DIR': 15,
    'MOTOR_B_STEP': 19,
    'MOTOR_B_DIR': 21,

    # Платформа (лоток)
    'TRAY_STEP': 18,        # CLK+ на драйвере
    'TRAY_DIR': 27,         # CW+. LOW=вперёд, HIGH=назад
    'TRAY_ENA_1': 25,       # OUTPUT LOW перед работой мотора
    'TRAY_ENA_2': 26,       # OUTPUT LOW перед работой мотора

    # Концевики XY
    'SENSOR_LEFT': 9,
    'SENSOR_RIGHT': 10,
    'SENSOR_BOTTOM': 8,
    'SENSOR_TOP': 11,

    # Концевики платформы
    'SENSOR_TRAY_END': 7,     # передний
    'SENSOR_TRAY_BEGIN': 20,   # задний (дребезг — нужен debounce)

    # Замки (сервоприводы PWM 50Гц)
    'LOCK_FRONT': 12,    # DutyCycle 2.5=открыт, 7.5=закрыт
    'LOCK_REAR': 13,     # DutyCycle 2.5=открыт, 7.5=закрыт

    # Шторки (реле)
    'SHUTTER_OUTER': 2,      # LOW=закрыта, HIGH=открыта (SDA1)
    'SHUTTER_INNER': 3,      # LOW=закрыта, HIGH=открыта (SCL1)

    # Алиасы для обратной совместимости
    'SERVO_LOCK_1': 12,   # = LOCK_FRONT
    'SERVO_LOCK_2': 13,   # = LOCK_REAR (НЕ путать с шторкой pin 13 в старых записях — замок подтверждён 11.03.2026)
    'SENSOR_X_BEGIN': 9,  # = SENSOR_LEFT
    'SENSOR_X_END': 10,   # = SENSOR_RIGHT
    'SENSOR_Y_BEGIN': 8,  # = SENSOR_BOTTOM
    'SENSOR_Y_END': 11,   # = SENSOR_TOP
}

# Границы XY
XY_BOUNDS = {
    'max_x': 19948,
    'max_y': 44853,
    'steps_per_mm': 100,
    'speed': 8000,
    'home': 'RIGHT_BOTTOM',
}

# Границы платформы
TRAY_BOUNDS = {
    'max_steps': 22000,
    'speed': 8000,
    'home': 'BACK',
    'debounce_reads': 3,
    'init_pins_low': [25, 26],
}


import os
MOCK_MODE = os.environ.get('MOCK_MODE', 'false').lower() == 'true'
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'
MOTOR_SPEEDS = {'xy': 4000, 'tray': 2000, 'acceleration': 8000}
MOTOR_DELAYS = {'xy': 0.000125, 'tray': 0.00025}
SERVO_ANGLES = {'lock1_open': 0, 'lock1_close': 95, 'lock2_open': 0, 'lock2_close': 95}
CABINET = {'rows': ['FRONT', 'BACK'], 'columns': 3, 'positions': 21, 'total_cells': 126, 'window': {'row': 'FRONT', 'x': 1, 'y': 9}}
TIMEOUTS = {'move': 1500, 'tray_extend': 800, 'tray_retract': 800, 'cell_open': 1000, 'cell_close': 1000, 'user_wait': 30000}
SENSOR_ACTIVE_HIGH = True
SENSOR_USE_PULLUP = True
BLOCKED_CELLS = {'FRONT': [], 'BACK': []}
RFID = {
    'nfc_card_reader': '/dev/pcsc',
    'uhf_card_reader': '/dev/ttyUSB1',
    'uhf_card_baudrate': 57600,
    'book_reader': '/dev/ttyUSB0',
    'book_baudrate': 57600,
    'uhf_card_reader_fallback': '/dev/ttyUSB1',
    'book_reader_fallback': '/dev/ttyUSB0',
    'card_poll_interval': 0.3,
    'card_debounce_ms': 800,
    'uhf_card_uid_length': 24,
}

IRBIS = {
    "host": os.environ.get("IRBIS_HOST", "172.29.67.70"),
    "port": int(os.environ.get("IRBIS_PORT", 6666)),
    "username": os.environ.get("IRBIS_USERNAME", "09f00st"),
    "password": os.environ.get("IRBIS_PASSWORD", "f00st"),
    "database": os.environ.get("IRBIS_DATABASE", "KAT%SERV09%"),
    "readers_database": os.environ.get("IRBIS_READERS_DB", "RDR"),
    "loan_days": int(os.environ.get("IRBIS_LOAN_DAYS", 30)),
    "location_code": os.environ.get("IRBIS_LOCATION_CODE", "09"),
    "mock": os.environ.get("IRBIS_MOCK", "false").lower() == "true",
}

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "/home/admin42/bookcabinet/logs/bookcabinet.log")

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/home/admin42/bookcabinet/data/bookcabinet.db")

