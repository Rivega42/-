#!/usr/bin/env python3
"""
Тестирование датчиков и концевиков BookCabinet
С агрессивным программным фильтром

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

# Состояние с гистерезисом
state = {name: 0 for name in SENSORS}

def read_stable(pin, samples=10):
    """Читает пин много раз, требует 80% согласия"""
    readings = sum(GPIO.input(pin) for _ in range(samples))
    # Нужно 8 из 10 одинаковых чтобы изменить состояние
    if readings >= 8:
        return 1
    elif readings <= 2:
        return 0
    return None  # Неопределённо

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    print("=" * 60)
    print("  МОНИТОРИНГ ДАТЧИКОВ (агрессивный фильтр)")
    print("=" * 60)
    print("PUD_DOWN | HIGH(1)=СРАБОТАЛ 🔴 | LOW(0)=свободен ⚪")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                val = read_stable(pin, samples=15)
                if val is not None:
                    state[name] = val
                icon = "🔴" if state[name] == 1 else "⚪"
                parts.append(f"{name}:{icon}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n--- ИТОГ ---")
        print("Моргание = нужны резисторы 4.7K-10K между GPIO и GND")
        print("Это аппаратная проблема, программный фильтр — костыль.")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
