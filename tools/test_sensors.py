#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
С гистерезисом для стабильного отображения

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

SAMPLES = 50
THRESHOLD_HIGH = 95  # ≥95% → сработал
THRESHOLD_LOW = 80   # ≤80% → свободен
                     # 80-95% → без изменений (гистерезис)

# Состояние датчиков
state = {name: False for name in SENSORS}

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def update_state(name, pct):
    """Обновляет состояние с гистерезисом"""
    if pct >= THRESHOLD_HIGH:
        state[name] = True
    elif pct <= THRESHOLD_LOW:
        state[name] = False
    # между 80-95% — не меняем

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 60)
    print("  МОНИТОРИНГ ДАТЧИКОВ TCST2103 (с гистерезисом)")
    print("=" * 60)
    print(f"Логика: ≥{THRESHOLD_HIGH}%=🔴 | ≤{THRESHOLD_LOW}%=⚪ | между=без изменений")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                update_state(name, pct)
                icon = "🔴" if state[name] else "⚪"
                parts.append(f"{name}:{icon}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nСостояние при выходе:")
        for name, pin in SENSORS.items():
            pct = read_percent(pin)
            status = "СРАБОТАЛ" if state[name] else "свободен"
            print(f"  {name}: {status} ({pct}%)")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
