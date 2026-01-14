#!/usr/bin/env python3
"""
Test TCST2103 sensors for BookCabinet
Individual step-by-step calibration

Usage: python3 tools/test_sensors.py              (monitor)
       python3 tools/test_sensors.py --calibrate  (calibrate all)
       python3 tools/test_sensors.py --step       (step-by-step)
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

DEFAULT_THRESHOLDS = {'high': 98, 'low': 89}

def load_calibration():
    thresholds = {name: DEFAULT_THRESHOLDS.copy() for name in SENSORS}
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, 'r') as f:
                saved = json.load(f)
                for name in SENSORS:
                    if name in saved:
                        thresholds[name] = saved[name]
            print(f"[OK] Loaded calibration from {CALIBRATION_FILE}")
        except Exception as e:
            print(f"[WARN] Load error: {e}")
    return thresholds

def save_calibration(thresholds):
    try:
        os.makedirs(os.path.dirname(CALIBRATION_FILE), exist_ok=True)
        with open(CALIBRATION_FILE, 'w') as f:
            json.dump(thresholds, f, indent=2)
        print(f"[OK] Saved to {CALIBRATION_FILE}")
    except Exception as e:
        print(f"[WARN] Save error: {e}")

state = {name: False for name in SENSORS}
pending = {name: None for name in SENSORS}
counter = {name: 0 for name in SENSORS}
thresholds = {}

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def update_state(name, pct):
    global state, pending, counter
    th = thresholds.get(name, DEFAULT_THRESHOLDS)
    
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

def safe_input(prompt):
    """Input with encoding error handling"""
    try:
        return input(prompt).strip().lower()
    except (UnicodeDecodeError, EOFError):
        return ''

def monitor_mode():
    global thresholds
    thresholds = load_calibration()
    
    print("\n" + "=" * 80)
    print("  SENSOR MONITOR")
    print("=" * 80)
    for name in SENSORS:
        th = thresholds[name]
        print(f"  {name}: high={th['high']}%, low={th['low']}%")
    print("\nCtrl+C to exit\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                update_state(name, pct)
                icon = "[X]" if state[name] else "[ ]"
                parts.append(f"{name}:{icon}{pct:3d}%")
            
            print(f"\r{' | '.join(parts)}", end="", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n")

def calibrate_one_sensor(name, pin):
    """Calibrate single sensor"""
    print(f"\n{'='*50}")
    print(f"  CALIBRATING: {name} (GPIO {pin})")
    print(f"{'='*50}")
    
    # Phase 1: open state
    print("\n[1/2] DO NOT PRESS sensor. Recording 'open' state...")
    print("      (5 sec)")
    
    open_values = []
    start = time.time()
    try:
        while time.time() - start < 5:
            pct = read_percent(pin)
            open_values.append(pct)
            remaining = 5 - int(time.time() - start)
            print(f"\r      Value: {pct:3d}%  [{remaining}s]  ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    
    if not open_values:
        print("\n[WARN] No data!")
        return None
    
    max_open = max(open_values)
    print(f"\n      Open: min={min(open_values)}%, max={max_open}%")
    
    # Phase 2: pressed state
    print("\n[2/2] PRESS AND HOLD sensor. Recording 'pressed' state...")
    print("      (5 sec)")
    
    pressed_values = []
    start = time.time()
    try:
        while time.time() - start < 5:
            pct = read_percent(pin)
            pressed_values.append(pct)
            remaining = 5 - int(time.time() - start)
            print(f"\r      Value: {pct:3d}%  [{remaining}s]  ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    
    if not pressed_values:
        print("\n[WARN] No data!")
        return None
    
    min_pressed = min(pressed_values)
    print(f"\n      Pressed: min={min_pressed}%, max={max(pressed_values)}%")
    
    # Result
    gap = min_pressed - max_open
    print(f"\n      Gap: {gap}%")
    
    if gap > 0:
        result = {
            'high': min_pressed,
            'low': max_open + 1
        }
        print(f"      [OK] Thresholds: high={result['high']}%, low={result['low']}%")
        return result
    else:
        print(f"      [WARN] No gap! Using default")
        return DEFAULT_THRESHOLDS.copy()

def step_calibrate_mode():
    """Step-by-step calibration"""
    print("=" * 60)
    print("  STEP-BY-STEP CALIBRATION")
    print("=" * 60)
    print("Calibrating each sensor individually.\n")
    
    current = load_calibration()
    sensor_list = list(SENSORS.items())
    
    for i, (name, pin) in enumerate(sensor_list):
        print(f"\n[{i+1}/{len(sensor_list)}] Sensor {name}")
        
        choice = safe_input("    Calibrate? (y/n/q=quit): ")
        
        if choice == 'q':
            break
        elif choice == 'y':
            result = calibrate_one_sensor(name, pin)
            if result:
                current[name] = result
        else:
            th = current[name]
            print(f"    Skipped. Current: high={th['high']}%, low={th['low']}%")
    
    # Summary
    print("\n" + "=" * 60)
    print("  FINAL THRESHOLDS")
    print("=" * 60)
    print(f"\n{'Sensor':<12} {'HIGH':<6} {'LOW':<6}")
    print("-" * 24)
    for name in SENSORS:
        th = current[name]
        print(f"{name:<12} {th['high']:<6} {th['low']:<6}")
    
    save = safe_input("\nSave? (y/n): ")
    if save == 'y':
        save_calibration(current)

def calibrate_all_mode():
    """Calibrate all at once"""
    stats = {name: {'min': 100, 'max': 0, 'values': []} for name in SENSORS}
    
    print("=" * 70)
    print("  CALIBRATE ALL SENSORS (30 sec)")
    print("=" * 70)
    print("Press all sensors multiple times. Ctrl+C to finish.\n")
    
    start_time = time.time()
    duration = 30
    
    try:
        while time.time() - start_time < duration:
            remaining = duration - int(time.time() - start_time)
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                stats[name]['min'] = min(stats[name]['min'], pct)
                stats[name]['max'] = max(stats[name]['max'], pct)
                stats[name]['values'].append(pct)
                parts.append(f"{name}:{pct:3d}%")
            print(f"\r[{remaining:2d}s] {' | '.join(parts)}", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    
    # Analysis
    print("\n\n" + "=" * 70)
    new_thresholds = {}
    
    for name in SENSORS:
        s = stats[name]
        open_vals = [v for v in s['values'] if v < 90]
        pressed_vals = [v for v in s['values'] if v >= 95]
        
        if open_vals and pressed_vals:
            max_open = max(open_vals)
            min_pressed = min(pressed_vals)
            if min_pressed > max_open:
                new_thresholds[name] = {'high': min_pressed, 'low': max_open + 1}
            else:
                new_thresholds[name] = DEFAULT_THRESHOLDS.copy()
        else:
            new_thresholds[name] = DEFAULT_THRESHOLDS.copy()
        
        th = new_thresholds[name]
        print(f"{name}: high={th['high']}%, low={th['low']}%")
    
    save = safe_input("\nSave? (y/n): ")
    if save == 'y':
        save_calibration(new_thresholds)

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    try:
        if '--step' in sys.argv or '-s' in sys.argv:
            step_calibrate_mode()
        elif '--calibrate' in sys.argv or '-c' in sys.argv:
            calibrate_all_mode()
        else:
            monitor_mode()
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
