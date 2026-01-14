#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
Логика без внешних резисторов: ≥95% HIGH = нажат

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

THRESHOLD = 95
SAMPLES = 50

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 60)
    print("  МОНИТОРИНГ ДАТЧИКОВ TCST2103")
    print("=" * 60)
    print(f"Логика: ≥{THRESHOLD}% = СРАБОТАЛ 🔴 | <{THRESHOLD}% = свободен ⚪")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                triggered = pct >= THRESHOLD
                icon = "🔴" if triggered else "⚪"
                parts.append(f"{name}:{icon}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nСостояние при выходе:")
        for name, pin in SENSORS.items():
            pct = read_percent(pin)
            status = "СРАБОТАЛ" if pct >= THRESHOLD else "свободен"
            print(f"  {name}: {status} ({pct}%)")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
