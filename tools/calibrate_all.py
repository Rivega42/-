#!/usr/bin/env python3
"""
calibrate_all.py — интерактивная калибровка ВСЕХ незаблокированных ячеек.

Проход: глубина 1 → стойки 1,2,3 → полки 1..20
        глубина 2 → стойки 1,2,3 → полки 1..20

В каждой точке:
  Enter / ok   — позиция верна, записать анкор
  y+100        — сдвиг Y вверх на 100 шагов
  y-50         — сдвиг Y вниз на 50 шагов
  x+50         — сдвиг X
  x+50 y-30    — одновременно
  s            — пропустить (не менять анкор)
  q            — выход (сохранить прогресс)

Скорость: 2000 шагов/сек
Лог: /tmp/calibrate_all_log.txt
"""
import sys, os, json, time, datetime, re

sys.path.insert(0, '/home/admin42/bookcabinet/tools')
from book_sequences import BookSequenceRunner, XY_CONFIG
from corexy_motion_v2 import MotionConfig

CAL_FILE = '/home/admin42/bookcabinet/calibration.json'
LOG_FILE = '/tmp/calibrate_all_log.txt'
SPEED = 2000

def log(msg):
    ts = datetime.datetime.now().strftime('%H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def load_cal():
    with open(CAL_FILE) as f:
        return json.load(f)

def save_cal(cal):
    with open(CAL_FILE, 'w') as f:
        json.dump(cal, f, indent=2, ensure_ascii=False)
    log('💾 сохранено')

def ensure_rack_y_anchors(cal):
    if 'rack_y_anchors' not in cal['shelves']:
        cal['shelves']['rack_y_anchors'] = {}
    for r in ['1', '2', '3']:
        if r not in cal['shelves']['rack_y_anchors']:
            cal['shelves']['rack_y_anchors'][r] = []

def get_rack_anchors(cal, rack):
    ensure_rack_y_anchors(cal)
    return cal['shelves']['rack_y_anchors'][str(rack)]

def update_rack_anchor(cal, rack, shelf, new_y):
    ensure_rack_y_anchors(cal)
    anchors = cal['shelves']['rack_y_anchors'][str(rack)]
    for a in anchors:
        if a['shelf'] == shelf:
            a['front_y'] = new_y
            a['back_y'] = new_y
            return
    anchors.append({'shelf': shelf, 'front_y': new_y, 'back_y': new_y})
    anchors.sort(key=lambda a: a['shelf'])

def interpolate_y_for_rack(cal, rack, shelf):
    """Интерполяция Y для стойки по её анкорам."""
    anchors = get_rack_anchors(cal, rack)
    if not anchors:
        anchors = cal['shelves']['anchors']

    lower = None
    upper = None
    for a in sorted(anchors, key=lambda x: x['shelf']):
        if a['shelf'] <= shelf:
            lower = a
        if a['shelf'] >= shelf and upper is None:
            upper = a

    if lower is None: return upper['front_y']
    if upper is None: return lower['front_y']
    if lower['shelf'] == upper['shelf']: return lower['front_y']

    t = (shelf - lower['shelf']) / (upper['shelf'] - lower['shelf'])
    return int(round(lower['front_y'] + t * (upper['front_y'] - lower['front_y'])))

def is_disabled(cal, depth, rack, shelf):
    addr = f'{depth}.{rack}.{shelf}'
    return addr in cal.get('disabled_cells', [])

def is_window(cal, depth, rack, shelf):
    return f'{depth}.{rack}.{shelf}' == cal.get('special_cells', {}).get('window')

def parse_cmd(ans):
    ans = ans.strip().lower()
    if ans in ('', 'ok'): return 'ok', 0, 0
    if ans == 's': return 'skip', 0, 0
    if ans == 'q': return 'quit', 0, 0
    dx, dy = 0, 0
    for m in re.finditer(r'([xy])([+-]\d+)', ans):
        axis, val = m.group(1), int(m.group(2))
        if axis == 'x': dx += val
        else: dy += val
    if dx != 0 or dy != 0:
        return 'move', dx, dy
    return 'unknown', 0, 0

def do_move(runner, cur_x, cur_y, dx, dy):
    if dx > 0:
        runner.motion.move(1, 1, dx, SPEED)
    elif dx < 0:
        runner.motion.move(0, 0, abs(dx), SPEED)
    if dx != 0: time.sleep(0.15)
    if dy > 0:
        runner.motion.move(1, 0, dy, SPEED)
    elif dy < 0:
        runner.motion.move(0, 1, abs(dy), SPEED)
    if dy != 0: time.sleep(0.15)
    return cur_x + dx, cur_y + dy

def ask(prompt):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        line = sys.stdin.buffer.readline().decode('utf-8', errors='replace')
    except Exception:
        line = sys.stdin.readline()
    if line == '':
        raise KeyboardInterrupt
    return line.strip()

def count_cells(cal):
    """Подсчёт незаблокированных ячеек."""
    total = 0
    for depth in [1, 2]:
        for rack in [1, 2, 3]:
            for shelf in range(1, 21):
                if not is_disabled(cal, depth, rack, shelf):
                    total += 1
    return total

def main():
    cal = load_cal()
    ensure_rack_y_anchors(cal)

    racks_x = {1: int(cal['racks']['1']),
               2: int(cal['racks']['2']),
               3: int(cal['racks']['3'])}

    total = count_cells(cal)

    with open(LOG_FILE, 'w') as f:
        f.write(f'=== calibrate_all {datetime.datetime.now()} ===\n')

    print('\n' + '='*60)
    print('  КАЛИБРОВКА ВСЕХ ЯЧЕЕК')
    print(f'  Скорость: {SPEED} шагов/сек')
    print(f'  Ячеек для обхода: ~{total}')
    print(f'  Порядок: depth1 (rack1→3, shelf1→20), depth2 (rack1→3, shelf1→20)')
    print()
    print('  Команды в каждой точке:')
    print('    Enter / ok   — позиция верна')
    print('    y+100        — выше на 100 шагов')
    print('    y-50         — ниже на 50 шагов')
    print('    x+50         — правее')
    print('    x+50 y-30    — X и Y одновременно')
    print('    s            — пропустить (анкор не меняется)')
    print('    q            — выход (прогресс сохранён)')
    print('='*60)

    r = ask('\nНачинаем? (y/n): ')
    if r.lower().strip() not in ('y', 'yes', 'д', 'да'):
        print('Отмена.')
        return

    runner = BookSequenceRunner()
    runner.motion = runner._init_motion()
    cur_x, cur_y = 0, 0
    done = 0

    try:
        for depth in [1, 2]:
            depth_label = 'ПЕРЕДНИЙ' if depth == 1 else 'ЗАДНИЙ'
            print(f'\n{"="*60}')
            print(f'  ГЛУБИНА {depth} ({depth_label})')
            print('='*60)

            for rack in [1, 2, 3]:
                x_target = racks_x[rack]
                print(f'\n  ── Стойка {rack} (X={x_target}) ──')
                log(f'Стойка {rack} (depth={depth})')

                # Едем к X стойки
                cur_x, cur_y = do_move(runner, cur_x, cur_y, x_target - cur_x, 0)
                time.sleep(0.2)

                for shelf in range(1, 21):
                    addr = f'{depth}.{rack}.{shelf}'

                    if is_disabled(cal, depth, rack, shelf):
                        continue
                    if is_window(cal, depth, rack, shelf):
                        log(f'  {addr} — окно, пропуск')
                        continue

                    y_target = interpolate_y_for_rack(cal, rack, shelf)
                    done += 1

                    # Едем к Y
                    cur_x, cur_y = do_move(runner, cur_x, cur_y, 0, y_target - cur_y)
                    time.sleep(0.2)

                    current_y = cur_y
                    current_x = cur_x

                    while True:
                        prompt = f'  [{addr}] ({done}/{total}) X={current_x} Y={current_y} → '
                        ans = ask(prompt)
                        action, dx, dy = parse_cmd(ans)

                        if action == 'quit':
                            raise KeyboardInterrupt
                        elif action == 'skip':
                            log(f'  {addr}: пропуск')
                            break
                        elif action == 'ok':
                            update_rack_anchor(cal, rack, shelf, current_y)
                            # X тоже обновляем если сдвигался
                            if current_x != racks_x[rack]:
                                cal['racks'][str(rack)] = current_x
                                racks_x[rack] = current_x
                                log(f'  {addr}: X обновлён → {current_x}')
                            log(f'  {addr}: OK Y={current_y}')
                            cur_y = current_y
                            cur_x = current_x
                            break
                        elif action == 'move':
                            cur_x, cur_y = do_move(runner, cur_x, cur_y, dx, dy)
                            current_y = cur_y
                            current_x = cur_x
                            log(f'  {addr}: сдвиг dx={dx:+d} dy={dy:+d} → X={cur_x} Y={cur_y}')
                        else:
                            print('    ? Примеры: ok, y+100, y-50, x+50, s, q')

                # Сохраняем после каждой стойки
                save_cal(cal)

    except KeyboardInterrupt:
        print('\n\n  Прерывание — сохраняю...')
        save_cal(cal)
    finally:
        try:
            runner.close()
        except:
            pass

    print(f'\n{"="*60}')
    print(f'  Готово! Откалибровано ячеек: {done}')
    print(f'  Лог: {LOG_FILE}')
    log('=== calibrate_all завершено ===')

if __name__ == '__main__':
    main()
