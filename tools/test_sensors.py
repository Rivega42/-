#!/usr/bin/env python3
"""
Тестирование датчиков TCST2103 BookCabinet
Индивидуальная калибровка каждого датчика

Запуск: python3 tools/test_sensors.py              (мониторинг)
        python3 tools/test_sensors.py --calibrate  (калибровка)
"""
import RPi.GPIO as GPIO
import time
import sys
import json
import os

SENSORS = {
    'X_BEGIN': 10,
    'X_END': 9,
    'Y_BEGIN': 11,
    'Y_END': 8,
    'TRAY_BEGIN': 7,
    'TRAY_END': 20,
}

SAMPLES = 50
DEBOUNCE_COUNT = 3
CALIBRATION_FILE = os.path.expanduser('~/bookcabinet/sensor_calibration.json')

# Дефолтные пороги (если нет калибровки)
DEFAULT_THRESHOLDS = {
    'high': 98,
    'low': 89,
}

# Загружаем калибровку
def load_calibration():
    """Загружает индивидуальные пороги для каждого датчика"""
    thresholds = {}
    for name in SENSORS:
        thresholds[name] = DEFAULT_THRESHOLDS.copy()
    
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                saved = json.load(f)
                for name in SENSORS:
                    if name in saved:
                        thresholds[name] = saved[name]
            print(f"✓ Загружена калибровка из {CALIBRATION_FILE}")
        except Exception as e:
            print(f"⚠ Ошибка загрузки калибровки: {e}")
    
    return thresholds

def save_calibration(thresholds):
    """Сохраняет калибровку в файл"""
    try:
        os.makedirs(os.path.dirname(CALIBRATION_FILE), exist_ok=True)
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(thresholds, f, indent=2)
        print(f"\n✓ Калибровка сохранена в {CALIBRATION_FILE}")
    except Exception as e:
        print(f"\n⚠ Ошибка сохранения: {e}")

# Состояние датчиков
state = {name: False for name in SENSORS}
pending = {name: None for name in SENSORS}
counter = {name: 0 for name in SENSORS}
thresholds = {}

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def update_state(name, pct):
    global state, pending, counter
    
    th = thresholds[name]
    if pct >= th['high']:
        desired = True
    elif pct <= th['low']:
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
    """Мониторинг в реальном времени с индивидуальными порогами"""
    global thresholds
    thresholds = load_calibration()
    
    print("\n" + "=" * 80)
    print("  МОНИТОРИНГ ДАТЧИКОВ (индивидуальные пороги)")
    print("=" * 80)
    print("Пороги:")
    for name in SENSORS:
        th = thresholds[name]
        print(f"  {name}: high={th['high']}%, low={th['low']}%")
    print("\nCtrl+C для выхода\n")
    
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
    """Калибровка каждого датчика отдельно"""
    stats = {name: {'min': 100, 'max': 0, 'values': []} for name in SENSORS}
    
    print("=" * 70)
    print("  КАЛИБРОВКА ДАТЧИКОВ TCST2103 (индивидуально)")
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
    
    # Анализ по каждому датчику
    print("\n\n" + "=" * 70)
    print("  РЕЗУЛЬТАТЫ КАЛИБРОВКИ (по каждому датчику)")
    print("=" * 70)
    
    new_thresholds = {}
    
    for name in SENSORS:
        s = stats[name]
        print(f"\n{name}:")
        print(f"  MIN: {s['min']:3d}%  |  MAX: {s['max']:3d}%")
        
        if s['max'] >= 95:
            # Разделяем на "открытые" и "нажатые" значения
            open_vals = [v for v in s['values'] if v < 90]
            pressed_vals = [v for v in s['values'] if v >= 95]
            
            if open_vals and pressed_vals:
                max_open = max(open_vals)
                min_pressed = min(pressed_vals)
                gap = min_pressed - max_open
                
                print(f"  Открыт: {min(open_vals)}-{max_open}%")
                print(f"  Нажат:  {min_pressed}-{max(pressed_vals)}%")
                print(f"  Зазор:  {gap}%")
                
                if gap > 0:
                    new_thresholds[name] = {
                        'high': min_pressed,
                        'low': max_open + 1
                    }
                    print(f"  ✓ Пороги: high={min_pressed}%, low={max_open + 1}%")
                else:
                    new_thresholds[name] = DEFAULT_THRESHOLDS.copy()
                    print(f"  ⚠ Нет зазора! Используем дефолт")
            else:
                new_thresholds[name] = DEFAULT_THRESHOLDS.copy()
                print(f"  ⚠ Недостаточно данных, используем дефолт")
        else:
            new_thresholds[name] = DEFAULT_THRESHOLDS.copy()
            print(f"  ⚠ Датчик не был нажат (max={s['max']}%)")
    
    # Сводная таблица
    print("\n" + "=" * 70)
    print("  ИТОГОВЫЕ ПОРОГИ")
    print("=" * 70)
    print(f"\n{'Датчик':<12} {'HIGH':<6} {'LOW':<6}")
    print("-" * 24)
    for name in SENSORS:
        th = new_thresholds[name]
        print(f"{name:<12} {th['high']:<6} {th['low']:<6}")
    
    # Сохранение
    print("\n" + "=" * 70)
    save = input("Сохранить калибровку? (y/n): ").strip().lower()
    if save == 'y':
        save_calibration(new_thresholds)
    else:
        print("Калибровка не сохранена")

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
