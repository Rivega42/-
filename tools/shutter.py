#!/usr/bin/env python3
"""
BookCabinet — управление шторками (standalone)

Использование:
    python3 shutter.py <shutter> <action>
    
Шторки:
    outer  — внешняя (GPIO 2)
    inner  — внутренняя (GPIO 3)
    both   — обе

Действия:
    open   — открыть (GPIO HIGH)
    close  — закрыть (GPIO LOW)
    state  — показать текущее состояние

Примеры:
    python3 shutter.py inner open
    python3 shutter.py outer close
    python3 shutter.py both open
    python3 shutter.py both state
"""
from __future__ import annotations
import sys
import time

try:
    import pigpio
except ImportError:
    print('ERROR: pigpio not installed', file=sys.stderr)
    sys.exit(1)

SHUTTERS = {
    'outer': 2,   # GPIO 2 (SDA1) — внешняя шторка
    'inner': 3,   # GPIO 3 (SCL1) — внутренняя шторка
}


def open_shutter(pi: pigpio.pi, name: str) -> None:
    pin = SHUTTERS[name]
    pi.set_mode(pin, pigpio.OUTPUT)
    pi.write(pin, 1)
    print(f'[shutter] {name} (GPIO {pin}) → OPEN (HIGH)')


def close_shutter(pi: pigpio.pi, name: str) -> None:
    pin = SHUTTERS[name]
    pi.set_mode(pin, pigpio.OUTPUT)
    pi.write(pin, 0)
    print(f'[shutter] {name} (GPIO {pin}) → CLOSE (LOW)')


def state_shutter(pi: pigpio.pi, name: str) -> None:
    pin = SHUTTERS[name]
    val = pi.read(pin)
    state = 'OPEN' if val == 1 else 'CLOSED'
    print(f'[shutter] {name} (GPIO {pin}) = {state} (level {val})')


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1

    shutter, action = sys.argv[1].lower(), sys.argv[2].lower()

    if shutter not in ('outer', 'inner', 'both'):
        print(f'ERROR: shutter must be outer|inner|both, got: {shutter}', file=sys.stderr)
        return 1

    if action not in ('open', 'close', 'state'):
        print(f'ERROR: action must be open|close|state, got: {action}', file=sys.stderr)
        return 1

    pi = pigpio.pi()
    if not pi.connected:
        print('ERROR: pigpiod not running', file=sys.stderr)
        return 1

    try:
        names = ['outer', 'inner'] if shutter == 'both' else [shutter]
        for name in names:
            if action == 'open':
                open_shutter(pi, name)
            elif action == 'close':
                close_shutter(pi, name)
            elif action == 'state':
                state_shutter(pi, name)
            time.sleep(0.1)
        return 0
    finally:
        pi.stop()


if __name__ == '__main__':
    sys.exit(main())
