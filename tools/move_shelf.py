#!/usr/bin/env python3
"""
BookCabinet — переместить полочку из одной ячейки в другую.

Универсальная обёртка над goto.py + shelf_operations.py с автоопределением
переднего/заднего ряда по первой цифре адреса (depth.rack.shelf).

Адрес: depth.rack.shelf
    depth=1 → передний ряд → extract_front / return_front
    depth=2 → задний ряд (с перехватом замков) → extract_rear / return_rear

Использование:
    python3 move_shelf.py <from> <to> [скорость]

Опции:
    --home       принудительный хоминг перед стартом
    --rear-from  принудительно использовать extract_rear (override автоопределения)
    --front-from принудительно использовать extract_front
    --rear-to    принудительно использовать return_rear
    --front-to   принудительно использовать return_front

Примеры:
    # Стандартная выдача — депт автоматически: 2.1.16 (back) → 1.2.9 (front)
    python3 move_shelf.py 2.1.16 1.2.9

    # Своя скорость (default 2600)
    python3 move_shelf.py 2.1.16 1.2.9 1500

    # Хоминг перед стартом
    python3 move_shelf.py --home 2.1.16 1.2.9

    # Override: вынуть как передний несмотря на адрес 2.x.x
    python3 move_shelf.py 2.1.16 1.2.9 --front-from
"""
from __future__ import annotations
import os
import sys
import subprocess

DEFAULT_SPEED = 2600
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
GOTO = os.path.join(TOOLS_DIR, 'goto.py')
SHELF_OPS = os.path.join(TOOLS_DIR, 'shelf_operations.py')


def parse_depth(address: str) -> int:
    """Получить depth из адреса depth.rack.shelf — первая цифра."""
    try:
        return int(address.split('.')[0])
    except (ValueError, IndexError):
        raise ValueError(f'Invalid address format: {address!r}, expected depth.rack.shelf')


def run(cmd: list[str]) -> int:
    print(f'\n>>> {" ".join(cmd)}')
    return subprocess.call(cmd)


def main() -> int:
    args = sys.argv[1:]

    # Флаги
    home = '--home' in args
    rear_from = '--rear-from' in args
    front_from = '--front-from' in args
    rear_to = '--rear-to' in args
    front_to = '--front-to' in args

    flags = ('--home', '--rear-from', '--front-from', '--rear-to', '--front-to')
    pos_args = [a for a in args if a not in flags]

    if len(pos_args) < 2:
        print(__doc__)
        return 1

    src = pos_args[0]
    dst = pos_args[1]
    speed = str(pos_args[2]) if len(pos_args) >= 3 else str(DEFAULT_SPEED)

    # Автоопределение по адресу с возможностью override
    src_depth = parse_depth(src)
    dst_depth = parse_depth(dst)

    if rear_from:
        extract_cmd = 'extract_rear'
    elif front_from:
        extract_cmd = 'extract_front'
    else:
        extract_cmd = 'extract_rear' if src_depth == 2 else 'extract_front'

    if rear_to:
        return_cmd = 'return_rear'
    elif front_to:
        return_cmd = 'return_front'
    else:
        return_cmd = 'return_rear' if dst_depth == 2 else 'return_front'

    print('=' * 60)
    print(f'  MOVE SHELF: {src} (depth={src_depth}) → {dst} (depth={dst_depth})')
    print(f'  speed={speed}, extract={extract_cmd}, return={return_cmd}')
    if home:
        print('  homing: ON')
    print('=' * 60)

    # Шаг 1: goto src
    goto_args = ['python3', GOTO]
    if home:
        goto_args += ['--home']
    goto_args += [speed, src]
    if run(goto_args) != 0:
        print('FAIL: goto src')
        return 1

    # Шаг 2: extract
    if run(['python3', SHELF_OPS, extract_cmd]) != 0:
        print('FAIL: extract')
        return 1

    # Шаг 3: goto dst (без хоминга)
    if run(['python3', GOTO, speed, dst]) != 0:
        print('FAIL: goto dst')
        return 1

    # Шаг 4: return
    if run(['python3', SHELF_OPS, return_cmd]) != 0:
        print('FAIL: return')
        return 1

    print('\n' + '=' * 60)
    print(f'  ✓ DONE: shelf moved {src} → {dst}')
    print('=' * 60)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nInterrupted')
        sys.exit(130)
