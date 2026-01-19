#!/usr/bin/env python3
"""
Тест шторок (через реле)
GPIO 14 (TX0) — Внешняя шторка
GPIO 15 (RX0) — Внутренняя шторка

Реле имеет своё питание, GPIO только коммутирует сигнал.
HIGH = реле включено = шторка открыта
LOW = реле выключено = шторка закрыта

Если логика инверсная (LOW = вкл), поменяй ACTIVE_HIGH на False
"""
import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run on Raspberry Pi!")
    sys.exit(1)

# Конфигурация
SHUTTER_OUTER = 14  # Внешняя
SHUTTER_INNER = 15  # Внутренняя

# Логика реле: True = HIGH включает, False = LOW включает
ACTIVE_HIGH = True


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    GPIO.setup(SHUTTER_OUTER, GPIO.OUT)
    GPIO.setup(SHUTTER_INNER, GPIO.OUT)
    
    # Начальное состояние — закрыты
    off_state = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH
    GPIO.output(SHUTTER_OUTER, off_state)
    GPIO.output(SHUTTER_INNER, off_state)


def shutter_on(pin, name=""):
    """Включить реле (открыть шторку)"""
    state = GPIO.HIGH if ACTIVE_HIGH else GPIO.LOW
    GPIO.output(pin, state)
    print(f"  {name}: ON (GPIO={state})")


def shutter_off(pin, name=""):
    """Выключить реле (закрыть шторку)"""
    state = GPIO.LOW if ACTIVE_HIGH else GPIO.HIGH
    GPIO.output(pin, state)
    print(f"  {name}: OFF (GPIO={state})")


def test_shutter(pin, name):
    """Тест одной шторки"""
    print(f"\n{'='*50}")
    print(f"  Testing {name}")
    print(f"{'='*50}")
    
    input(f"Press Enter to OPEN {name}...")
    shutter_on(pin, name)
    
    input(f"Press Enter to CLOSE {name}...")
    shutter_off(pin, name)
    
    print(f"  {name} test complete!")


def interactive_mode():
    """Интерактивный режим"""
    print("\n" + "="*50)
    print("  INTERACTIVE MODE")
    print("="*50)
    print("Commands:")
    print("  oo / oc  — Outer open/close")
    print("  io / ic  — Inner open/close")
    print("  ao / ac  — All open/close")
    print("  t        — Toggle ACTIVE_HIGH logic")
    print("  s        — Show current state")
    print("  q        — Quit")
    print()
    
    global ACTIVE_HIGH
    
    while True:
        try:
            cmd = input("Command: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        
        if cmd == 'q':
            break
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
            time.sleep(0.2)
            shutter_on(SHUTTER_OUTER, "Outer")
        elif cmd == 'ac':
            shutter_off(SHUTTER_OUTER, "Outer")
            time.sleep(0.2)
            shutter_off(SHUTTER_INNER, "Inner")
        elif cmd == 't':
            ACTIVE_HIGH = not ACTIVE_HIGH
            print(f"  ACTIVE_HIGH = {ACTIVE_HIGH}")
            print(f"  (HIGH = {'ON' if ACTIVE_HIGH else 'OFF'})")
        elif cmd == 's':
            outer = GPIO.input(SHUTTER_OUTER)
            inner = GPIO.input(SHUTTER_INNER)
            print(f"  Outer GPIO {SHUTTER_OUTER}: {'HIGH' if outer else 'LOW'}")
            print(f"  Inner GPIO {SHUTTER_INNER}: {'HIGH' if inner else 'LOW'}")
            print(f"  ACTIVE_HIGH = {ACTIVE_HIGH}")
        else:
            print("  Unknown command")


def main():
    print("="*50)
    print("  SHUTTER RELAY TEST")
    print("="*50)
    print(f"Outer shutter: GPIO {SHUTTER_OUTER}")
    print(f"Inner shutter: GPIO {SHUTTER_INNER}")
    print(f"Active HIGH: {ACTIVE_HIGH} (HIGH = relay ON)")
    
    setup()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '-i':
            interactive_mode()
        else:
            test_shutter(SHUTTER_OUTER, "Outer shutter")
            test_shutter(SHUTTER_INNER, "Inner shutter")
            
            print("\n" + "="*50)
            print("  Run with -i for interactive mode")
            print("="*50)
    finally:
        # Закрыть все шторки
        shutter_off(SHUTTER_OUTER, "Outer")
        shutter_off(SHUTTER_INNER, "Inner")
        GPIO.cleanup()
        print("\nGPIO cleanup done.")


if __name__ == '__main__':
    main()
