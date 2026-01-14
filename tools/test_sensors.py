#!/usr/bin/env python3
"""
Тестирование датчиков и концевиков BookCabinet
Отображает состояние в реальном времени

Запуск: python3 tools/test_sensors.py
"""
import RPi.GPIO as GPIO
import time
import sys

# Датчики из config.py
SENSORS = {
    'X_BEGIN': 10,    # Левый концевик (MOSI)
    'X_END': 9,       # Правый концевик (MISO)
    'Y_BEGIN': 11,    # Нижний концевик (SCLK)
    'Y_END': 8,       # Верхний концевик (CE0)
    'TRAY_BEGIN': 7,  # Платформа назад (CE1)
    'TRAY_END': 20,   # Платформа вперёд (PCMi)
}

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for name, pin in SENSORS.items():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    print("GPIO инициализирован с PUD_UP")

def main():
    setup()
    print("\nМониторинг датчиков (Ctrl+C для выхода)")
    print("Логика: LOW(0)=СРАБОТАЛ, HIGH(1)=свободен\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                val = GPIO.input(pin)
                # LOW = сработал (замкнут на GND)
                icon = "🔴" if val == 0 else "⚪"
                parts.append(f"{name}:{icon}({val})")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\n\nВыход...")
    finally:
        GPIO.cleanup()
        print("GPIO очищен")

if __name__ == '__main__':
    main()
