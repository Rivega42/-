#!/usr/bin/env python3
"""
goto.py — переставить каретку в заданную позицию.

Позиция сохраняется в /tmp/carriage_pos.json после каждого движения.
При следующем вызове — едет дельтой без хоминга.
После перезагрузки RPi (файл исчезает) — автоматический хоминг.

Использование:
  python3 goto.py <позиция>              # скорость 800, без хоминга если знаем позицию
  python3 goto.py <скорость> <позиция>   # своя скорость
  python3 goto.py --home <позиция>       # принудительный хоминг перед движением
  python3 goto.py --home 400 <позиция>   # хоминг + своя скорость

Примеры:
  python3 goto.py 1.3.5
  python3 goto.py 400 1.3.5
  python3 goto.py --home 1.3.5
  python3 goto.py --home 400 1.3.5
"""
import sys
import time
import json
import os

POS_FILE = '/tmp/carriage_pos.json'

sys.path.insert(0, '/home/admin42/bookcabinet/tools')
from corexy_motion_v2 import CoreXYMotionV2, MotionConfig
from calibration import resolve_cell

# ── Парсим аргументы ──────────────────────────────────────────
args = sys.argv[1:]

force_home = False
if '--home' in args:
    force_home = True
    args.remove('--home')

if len(args) == 1:
    speed = 800
    address = args[0]
elif len(args) == 2:
    try:
        speed = int(args[0])
        address = args[1]
    except ValueError:
        print(f'Ошибка: первый аргумент должен быть скоростью (число), получено "{args[0]}"')
        sys.exit(1)
else:
    print('Использование:')
    print('  python3 goto.py <позиция>')
    print('  python3 goto.py <скорость> <позиция>')
    print('  python3 goto.py --home <позиция>')
    print('  python3 goto.py --home <скорость> <позиция>')
    print('Пример: python3 goto.py 400 1.3.5')
    sys.exit(1)

if speed < 100 or speed > 3000:
    print(f'Ошибка: скорость {speed} вне диапазона 100–3000')
    sys.exit(1)

# ── Целевая позиция ───────────────────────────────────────────
try:
    target_x, target_y = resolve_cell(address)
except Exception as e:
    print(f'Ошибка позиции {address}: {e}')
    sys.exit(1)

# ── Текущая позиция ───────────────────────────────────────────
def load_pos():
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE) as f:
                d = json.load(f)
            return d['x'], d['y']
        except Exception:
            pass
    return None, None

def save_pos(x, y, address):
    with open(POS_FILE, 'w') as f:
        json.dump({'x': x, 'y': y, 'address': address}, f)

cur_x, cur_y = load_pos()
need_home = force_home or (cur_x is None)

if need_home:
    if force_home:
        print(f'Позиция: {address} → x={target_x} y={target_y} | скорость={speed} | хоминг: принудительный')
    else:
        print(f'Позиция: {address} → x={target_x} y={target_y} | скорость={speed} | хоминг: нет файла позиции')
else:
    print(f'Позиция: {address} → x={target_x} y={target_y} | скорость={speed} | из x={cur_x} y={cur_y} (без хоминга)')

# ── Движение ──────────────────────────────────────────────────
cfg = MotionConfig(fast=speed, homing_fast=1800, slow=300, backoff_x=300, backoff_y=500)
motion = CoreXYMotionV2(config=cfg)

if need_home:
    print('Хоминг...')
    motion.home_xy()
    cur_x, cur_y = 0, 0

# Считаем дельты от текущей позиции
dx = target_x - cur_x
dy = target_y - cur_y

if dx > 0:
    print(f'Еду X +{dx}...')
    motion.move(1, 1, dx, cfg.fast)
    time.sleep(0.2)
elif dx < 0:
    print(f'Еду X {dx}...')
    motion.move(0, 0, abs(dx), cfg.fast)
    time.sleep(0.2)

if dy > 0:
    print(f'Еду Y +{dy}...')
    motion.move(1, 0, dy, cfg.fast)
    time.sleep(0.2)
elif dy < 0:
    print(f'Еду Y {dy}...')
    motion.move(0, 1, abs(dy), cfg.fast)
    time.sleep(0.2)

# Сохраняем новую позицию
save_pos(target_x, target_y, address)
motion.close()

print(f'Готово — каретка в {address} (x={target_x} y={target_y})')
