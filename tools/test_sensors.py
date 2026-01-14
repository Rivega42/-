#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
Логика без внешних резисторов: 100%=нажат, <95%=открыт

Запуск: python3 tools/test_sensors.py
"""
import RPi.GPIO as GPIO
import time

SENSORS = {
    'X_BEGIN': 10,
    'X_END': 9,
    'Y_BEGIN': 11,
    'Y_END': 8,
    'TRAY_BEGIN': 7,
    'TRAY_END': 20,
}

THRESHOLD = 95  # % для определения "нажат"
SAMPLES = 50    # Количество чтений для усреднения

def read_sensor(pin):
    """Читает датчик, возвращает True если нажат (>=95% HIGH)"""
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    percent = readings * 100 // SAMPLES
    return percent >= THRESHOLD

def read_all_sensors():
    """Возвращает словарь {имя: True/False}"""
    return {name: read_sensor(pin) for name, pin in SENSORS.items()}

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 60)
    print("  МОНИТОРИНГ ДАТЧИКОВ TCST2103")
    print("=" * 60)
    print(f"Логика: ≥{THRESHOLD}% HIGH = СРАБОТАЛ 🔴 | <{THRESHOLD}% = свободен ⚪")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            sensors = read_all_sensors()
            parts = []
            for name, triggered in sensors.items():
                icon = "🔴" if triggered else "⚪"
                parts.append(f"{name}:{icon}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nСостояние при выходе:")
        sensors = read_all_sensors()
        for name, triggered in sensors.items():
            status = "СРАБОТАЛ" if triggered else "свободен"
            print(f"  {name}: {status}")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
