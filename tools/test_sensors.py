#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
Калиброванные пороги: 98/89%, debounce 3

Запуск: python3 tools/test_sensors.py
        python3 tools/test_sensors.py --calibrate  (режим калибровки)
"""
import RPi.GPIO as GPIO
import time
import sys

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
THRESHOLD_LOW = 89
DEBOUNCE_COUNT = 3

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

def monitor_mode():
    """Мониторинг в реальном времени"""
    print("=" * 75)
    print("  МОНИТОРИНГ ДАТЧИКОВ (калибровка: 98/89%, debounce 3)")
    print("=" * 75)
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

def calibrate_mode():
    """Режим калибровки — запись значений"""
    stats = {name: {'min': 100, 'max': 0, 'values': []} for name in SENSORS}
    
    print("=" * 70)
    print("  КАЛИБРОВКА ДАТЧИКОВ TCST2103")
    print("=" * 70)
    print("Понажимай все датчики несколько раз.")
    print("Через 30 сек или по Ctrl+C — выведу рекомендации.\n")
    
    start_time = time.time()
    duration = 30
    
    try:
        while time.time() - start_time < duration:
            elapsed = int(time.time() - start_time)
            remaining = duration - elapsed
            
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                stats[name]['min'] = min(stats[name]['min'], pct)
                stats[name]['max'] = max(stats[name]['max'], pct)
                stats[name]['values'].append(pct)
                parts.append(f"{name}:{pct:3d}%")
            
            print(f"\r[{remaining:2d}с] {' | '.join(parts)}", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
    
    # Анализ
    print("\n\n" + "=" * 70)
    print("  РЕЗУЛЬТАТЫ КАЛИБРОВКИ")
    print("=" * 70)
    
    all_max_open = 0
    all_min_pressed = 100
    
    for name in SENSORS:
        s = stats[name]
        print(f"\n{name}:")
        print(f"  MIN: {s['min']:3d}%  |  MAX: {s['max']:3d}%  |  Диапазон: {s['max'] - s['min']}%")
        
        if s['max'] >= 98:
            open_vals = [v for v in s['values'] if v < 90]
            pressed_vals = [v for v in s['values'] if v >= 98]
            
            if open_vals:
                all_max_open = max(all_max_open, max(open_vals))
            if pressed_vals:
                all_min_pressed = min(all_min_pressed, min(pressed_vals))
                
            print(f"  Открыт: {min(open_vals) if open_vals else '?'}-{max(open_vals) if open_vals else '?'}%")
            print(f"  Нажат:  {min(pressed_vals) if pressed_vals else '?'}-{max(pressed_vals) if pressed_vals else '?'}%")
        else:
            print(f"  ⚠ Датчик не был нажат (max < 98%)")
    
    print("\n" + "=" * 70)
    print("  РЕКОМЕНДАЦИИ")
    print("=" * 70)
    
    if all_max_open < all_min_pressed:
        gap = all_min_pressed - all_max_open
        threshold_high = all_min_pressed
        threshold_low = all_max_open + 1
        
        print(f"\n✓ Чёткое разделение! Зазор: {gap}%")
        print(f"\n  Открыт:  0% — {all_max_open}%")
        print(f"  Нажат:   {all_min_pressed}% — 100%")
        print(f"\n  РЕКОМЕНДУЕМЫЕ ПОРОГИ:")
        print(f"    THRESHOLD_HIGH = {threshold_high}")
        print(f"    THRESHOLD_LOW  = {threshold_low}")
        print(f"    DEBOUNCE_COUNT = 3")
    else:
        print(f"\n⚠ Нет чёткого разделения!")
        print(f"  Попробуй увеличить DEBOUNCE_COUNT до 5-10")

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    try:
        if '--calibrate' in sys.argv or '-c' in sys.argv:
            calibrate_mode()
        else:
            monitor_mode()
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
