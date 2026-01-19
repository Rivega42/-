#!/usr/bin/env python3
"""
Тест шторок (через реле)
GPIO 14 (TX0) — Внешняя шторка
GPIO 15 (RX0) — Внутренняя шторка

+ Мониторинг всех концевиков для проверки наводок
"""
import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run on Raspberry Pi!")
    sys.exit(1)

# Конфигурация шторок
SHUTTER_OUTER = 14  # Внешняя
SHUTTER_INNER = 15  # Внутренняя

# Логика реле: True = HIGH включает, False = LOW включает
ACTIVE_HIGH = True

# Конфигурация датчиков
SENSORS = {
    'X_BEGIN': 10,
    'X_END': 9,
    'Y_BEGIN': 11,
    'Y_END': 8,
    'TRAY_BEGIN': 7,
    'TRAY_END': 20,
}

THRESHOLDS = {
    'X_BEGIN': {'high': 95, 'low': 85},
    'X_END': {'high': 95, 'low': 85},
    'Y_BEGIN': {'high': 95, 'low': 85},
    'Y_END': {'high': 95, 'low': 85},
    'TRAY_BEGIN': {'high': 95, 'low': 85},
    'TRAY_END': {'high': 95, 'low': 85},
}

SAMPLES = 50


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Шторки
    GPIO.setup(SHUTTER_OUTER, GPIO.OUT)
    GPIO.setup(SHUTTER_INNER, GPIO.OUT)
    
    off_state = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH
    GPIO.output(SHUTTER_OUTER, off_state)
    GPIO.output(SHUTTER_INNER, off_state)
    
    # Датчики
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def read_sensor_percent(pin, samples=SAMPLES):
    """Читает датчик и возвращает % HIGH"""
    high_count = sum(1 for _ in range(samples) if GPIO.input(pin) == GPIO.HIGH)
    return int(high_count * 100 / samples)


def get_sensor_state(name, percent):
    """Определяет состояние датчика по порогам"""
    th = THRESHOLDS.get(name, {'high': 95, 'low': 85})
    if percent >= th['high']:
        return '🔴'
    elif percent <= th['low']:
        return '⚪'
    else:
        return '🟡'


def print_sensors(prefix=""):
    """Вывести состояние всех датчиков"""
    parts = []
    for name, pin in SENSORS.items():
        pct = read_sensor_percent(pin)
        state = get_sensor_state(name, pct)
        parts.append(f"{name}:{state}{pct:3d}%")
    print(f"{prefix}[{' | '.join(parts)}]")


def shutter_on(pin, name=""):
    """Включить реле (открыть шторку)"""
    state = GPIO.HIGH if ACTIVE_HIGH else GPIO.LOW
    GPIO.output(pin, state)
    print(f"  {name}: ON (GPIO={'HIGH' if state else 'LOW'})")
    time.sleep(0.3)
    print_sensors("  Sensors: ")


def shutter_off(pin, name=""):
    """Выключить реле (закрыть шторку)"""
    state = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH
    GPIO.output(pin, state)
    print(f"  {name}: OFF (GPIO={'HIGH' if state else 'LOW'})")
    time.sleep(0.3)
    print_sensors("  Sensors: ")


def test_shutter(pin, name):
    """Тест одной шторки"""
    print(f"\n{'='*60}")
    print(f"  Testing {name}")
    print(f"{'='*60}")
    
    print_sensors("  Before: ")
    
    input(f"Press Enter to OPEN {name}...")
    shutter_on(pin, name)
    
    input(f"Press Enter to CLOSE {name}...")
    shutter_off(pin, name)
    
    print(f"  {name} test complete!")


def interactive_mode():
    """Интерактивный режим"""
    print("\n" + "="*60)
    print("  INTERACTIVE MODE")
    print("="*60)
    print("Commands:")
    print("  oo / oc  — Outer open/close")
    print("  io / ic  — Inner open/close")
    print("  ao / ac  — All open/close")
    print("  t        — Toggle ACTIVE_HIGH logic")
    print("  s        — Show sensors")
    print("  q        — Quit")
    print()
    
    global ACTIVE_HIGH
    print_sensors("Initial: ")
    
    while True:
        try:
            cmd = input("Command: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        
        if cmd == 'q':
            break
        elif cmd == 's':
            print_sensors("Sensors: ")
        elif cmd == 'oo':
            shutter_on(SHUTTER_OUTER, "Outer")
        elif cmd == 'oc':
            shutter_off(SHUTTER_OUTER, "Outer")
        elif cmd == 'io':
            shutter_on(SHUTTER_INNER, "Inner")
        elif cmd == 'ic':
            shutter_off(SHUTTER_INNER, "Inner")
        elif cmd == 'ao':
            shutter_on(SHUTTER_INNER, "Inner")
            shutter_on(SHUTTER_OUTER, "Outer")
        elif cmd == 'ac':
            shutter_off(SHUTTER_OUTER, "Outer")
            shutter_off(SHUTTER_INNER, "Inner")
        elif cmd == 't':
            ACTIVE_HIGH = not ACTIVE_HIGH
            print(f"  ACTIVE_HIGH = {ACTIVE_HIGH}")
            print(f"  (HIGH = {'ON' if ACTIVE_HIGH else 'OFF'})")
        else:
            print("  Unknown command")


def main():
    print("="*60)
    print("  SHUTTER RELAY TEST + SENSOR MONITOR")
    print("="*60)
    print(f"Outer shutter: GPIO {SHUTTER_OUTER}")
    print(f"Inner shutter: GPIO {SHUTTER_INNER}")
    print(f"Active HIGH: {ACTIVE_HIGH}")
    print(f"Sensors: {', '.join(SENSORS.keys())}")
    
    setup()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '-i':
            interactive_mode()
        else:
            test_shutter(SHUTTER_OUTER, "Outer shutter")
            test_shutter(SHUTTER_INNER, "Inner shutter")
            
            print("\n" + "="*60)
            print("  Run with -i for interactive mode")
            print("="*60)
    finally:
        shutter_off(SHUTTER_OUTER, "Outer")
        shutter_off(SHUTTER_INNER, "Inner")
        GPIO.cleanup()
        print("\nGPIO cleanup done.")


if __name__ == '__main__':
    main()
