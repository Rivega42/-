#!/usr/bin/env python3
"""
Тестирование датчиков и концевиков BookCabinet
С программным фильтром от наводок

Запуск: python3 tools/test_sensors.py
"""
import RPi.GPIO as GPIO
import time

SENSORS = {
    'X_BEGIN': 10,    # Левый концевик
    'X_END': 9,       # Правый концевик
    'Y_BEGIN': 11,    # Нижний концевик
    'Y_END': 8,       # Верхний концевик
    'TRAY_BEGIN': 7,  # Платформа назад
    'TRAY_END': 20,   # Платформа вперёд
}

def read_filtered(pin, samples=5, delay=0.002):
    """Читает пин несколько раз и возвращает majority vote"""
    readings = []
    for _ in range(samples):
        readings.append(GPIO.input(pin))
        time.sleep(delay)
    # Большинство голосов
    return 1 if sum(readings) > samples // 2 else 0

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    print("=" * 60)
    print("  МОНИТОРИНГ ДАТЧИКОВ (с фильтром)")
    print("=" * 60)
    print("Логика: HIGH(1)=СРАБОТАЛ 🔴, LOW(0)=свободен ⚪")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                val = read_filtered(pin, samples=5)
                icon = "🔴" if val == 1 else "⚪"
                parts.append(f"{name}:{icon}({val})")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nВыход...")
    finally:
        GPIO.cleanup()
        print("GPIO очищен")

if __name__ == '__main__':
    main()
