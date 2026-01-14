#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
С гистерезисом + временной фильтр (debounce) + проценты

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
THRESHOLD_HIGH = 98
THRESHOLD_LOW = 95
DEBOUNCE_COUNT = 5

# Состояние датчиков
state = {name: False for name in SENSORS}
pending = {name: None for name in SENSORS}
counter = {name: 0 for name in SENSORS}

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def update_state(name, pct):
    global state, pending, counter
    
    if pct >= THRESHOLD_HIGH:
        desired = True
    elif pct <= THRESHOLD_LOW:
        desired = False
    else:
        desired = state[name]
    
    if desired == pending[name]:
        counter[name] += 1
    else:
        pending[name] = desired
        counter[name] = 1
    
    if counter[name] >= DEBOUNCE_COUNT and state[name] != desired:
        state[name] = desired

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 75)
    print("  МОНИТОРИНГ ДАТЧИКОВ (гистерезис + debounce)")
    print("=" * 75)
    print(f"Порог: ≥{THRESHOLD_HIGH}%=🔴 | ≤{THRESHOLD_LOW}%=⚪ | Debounce: {DEBOUNCE_COUNT}")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                update_state(name, pct)
                icon = "🔴" if state[name] else "⚪"
                parts.append(f"{name}:{icon}{pct:3d}%")
            
            print(f"\r{' | '.join(parts)}", end="", flush=True)
            time.sleep(0.05)
            
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
