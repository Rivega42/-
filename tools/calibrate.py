#!/usr/bin/env python3
"""
calibrate.py — полная калибровка X стоек и Y полок (per-rack).

Фаза 1: X-калибровка 3 стоек (на полке 5)
Фаза 2: Y-калибровка опорных полок (1,3,5,7,10,14,18,21) в каждой стойке
        Каждая стойка имеет СВОИ анкоры Y — перекос рамы/ремней учитывается.
        Остальные полки — линейная интерполяция между опорами стойки.

Управление в каждой точке:
  Enter / ok   — позиция верна
  x+100        — сдвиг X на +100 шагов
  x-50         — сдвиг X на -50 шагов
  y+200        — сдвиг Y на +200 шагов
  y-100        — сдвиг Y на -100 шагов
  x+100 y-50   — сдвиг X и Y одновременно
  s            — пропустить точку
  q            — выход (сохраняет прогресс)

Лог пишется в /tmp/calibration_log.txt
"""
import sys, os, json, time, datetime, re

sys.path.insert(0, '/home/admin42/bookcabinet/tools')
from book_sequences import BookSequenceRunner, XY_CONFIG
from corexy_motion_v2 import MotionConfig
XY_CONFIG = MotionConfig(fast=2600, homing_fast=1800, slow=300, backoff_x=300, backoff_y=500)

CAL_FILE = '/home/admin42/bookcabinet/calibration.json'
LOG_FILE = '/tmp/calibration_log.txt'

ANCHOR_SHELVES = [1, 3, 5, 7, 10, 14, 18, 21]

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
    log('💾 calibration.json сохранён')

def ensure_rack_y_anchors(cal):
    """Инициализируем rack_y_anchors если нет."""
    if 'rack_y_anchors' not in cal['shelves']:
        cal['shelves']['rack_y_anchors'] = {'1': [], '2': [], '3': []}
    for r in ['1', '2', '3']:
        if r not in cal['shelves']['rack_y_anchors']:
            cal['shelves']['rack_y_anchors'][r] = []

def get_rack_anchors(cal, rack: int) -> list:
    """Получить анкоры для стойки (per-rack)."""
    ensure_rack_y_anchors(cal)
    return cal['shelves']['rack_y_anchors'][str(rack)]

def update_rack_anchor(cal, rack: int, shelf: int, new_y: int):
    """Обновить или добавить анкор для конкретной стойки."""
    ensure_rack_y_anchors(cal)
    anchors = cal['shelves']['rack_y_anchors'][str(rack)]
    for a in anchors:
        if a['shelf'] == shelf:
            a['front_y'] = new_y
            a['back_y'] = new_y
            return
    anchors.append({'shelf': shelf, 'front_y': new_y, 'back_y': new_y})
    anchors.sort(key=lambda a: a['shelf'])

def interpolate_from_anchors(shelf: int, anchors: list) -> int:
    """Линейная интерполяция Y по анкорам."""
    if not anchors:
        return 0
    lower = None
    upper = None
    for a in sorted(anchors, key=lambda x: x['shelf']):
        if a['shelf'] <= shelf:
            lower = a
        if a['shelf'] >= shelf and upper is None:
            upper = a
    if lower is None:
        return upper['front_y']
    if upper is None:
        return lower['front_y']
    if lower['shelf'] == upper['shelf']:
        return lower['front_y']
    t = (shelf - lower['shelf']) / (upper['shelf'] - lower['shelf'])
    return int(round(lower['front_y'] + t * (upper['front_y'] - lower['front_y'])))

def build_y_table_for_rack(cal, rack: int) -> dict:
    """Таблица Y[0..21] для конкретной стойки."""
    anchors = get_rack_anchors(cal, rack)
    if not anchors:
        # Фолбэк на общие анкоры
        anchors = cal['shelves']['anchors']
    result = {}
    for s in range(22):
        result[s] = interpolate_from_anchors(s, anchors)
    return result

def is_disabled(cal, rack, shelf):
    d1 = f'1.{rack}.{shelf}' not in cal['disabled_cells']
    d2 = f'2.{rack}.{shelf}' not in cal['disabled_cells']
    win = f'1.{rack}.{shelf}' == cal['special_cells'].get('window')
    return not (d1 or d2) or win

def parse_cmd(ans):
    ans = ans.strip().lower()
    if ans in ('', 'ok'):
        return 'ok', 0, 0
    if ans == 's':
        return 'skip', 0, 0
    if ans == 'q':
        return 'quit', 0, 0
    dx, dy = 0, 0
    for m in re.finditer(r'([xy])([+-]\d+)', ans):
        axis, val = m.group(1), int(m.group(2))
        if axis == 'x':
            dx += val
        else:
            dy += val
    if dx != 0 or dy != 0:
        return 'move', dx, dy
    return 'unknown', 0, 0

def do_move(runner, cur_x, cur_y, dx, dy):
    if dx > 0:
        runner.motion.move(1, 1, dx, XY_CONFIG.fast)
    elif dx < 0:
        runner.motion.move(0, 0, abs(dx), XY_CONFIG.fast)
    if dx != 0:
        time.sleep(0.2)
    if dy > 0:
        runner.motion.move(1, 0, dy, XY_CONFIG.fast)
    elif dy < 0:
        runner.motion.move(0, 1, abs(dy), XY_CONFIG.fast)
    if dy != 0:
        time.sleep(0.2)
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

def main():
    cal = load_cal()
    ensure_rack_y_anchors(cal)

    racks_x = {1: int(cal['racks']['1']),
               2: int(cal['racks']['2']),
               3: int(cal['racks']['3'])}

    with open(LOG_FILE, 'w') as f:
        f.write(f'=== Калибровка {datetime.datetime.now()} ===\n')

    print('\n' + '='*60)
    print('  КАЛИБРОВКА BookCabinet (per-rack Y)')
    print('  Фаза 1: X стоек (3 точки на полке 5)')
    print('  Фаза 2: Y опорных полок — КАЖДАЯ СТОЙКА ОТДЕЛЬНО')
    print()
    print('  Команды:')
    print('    Enter / ok   — позиция верна')
    print('    x+100        — сдвиг X на +100 шагов')
    print('    x-50         — сдвиг X на -50 шагов')
    print('    y+200        — сдвиг Y на +200 шагов')
    print('    x+100 y-50   — сдвиг X и Y одновременно')
    print('    s            — пропустить точку')
    print('    q            — выход (сохраняет прогресс)')
    print('='*60)

    r = ask('\nНачинаем? (y/n): ')
    if r.lower().strip() not in ('y', 'yes', 'д', 'да'):
        print('Отмена.')
        return

    runner = BookSequenceRunner()
    runner._init_motion()
    cur_x, cur_y = 0, 0

    try:
        # ══════════════════════════════════════════
        # ФАЗА 1: X-калибровка стоек
        # ══════════════════════════════════════════
        print('\n' + '='*60)
        print('  ФАЗА 1: Калибровка X стоек (на полке 5)')
        print('='*60)
        log('=== ФАЗА 1: X-калибровка ===')

        # Стартовый Y полки 5 — из анкоров стойки 1 или общих
        y_table_r1 = build_y_table_for_rack(cal, 1)
        shelf5_y = y_table_r1[5]
        calibrated_shelf5_y = shelf5_y

        for rack in [1, 2, 3]:
            x_target = racks_x[rack]
            target_y = calibrated_shelf5_y
            log(f'Стойка {rack}: едем X={x_target}, Y={target_y}')
            print(f'\n--- Стойка {rack} ---')
            print(f'  Еду X={x_target}, Y={target_y}...')

            cur_x, cur_y = do_move(runner, cur_x, cur_y, x_target - cur_x, target_y - cur_y)
            time.sleep(0.3)

            current_x = cur_x
            while True:
                ans = ask(f'  [Стойка {rack}] X={current_x} Y={cur_y} → ')
                action, dx, dy = parse_cmd(ans)

                if action == 'quit':
                    raise KeyboardInterrupt
                elif action == 'skip':
                    log(f'Стойка {rack} X: пропущено')
                    break
                elif action == 'ok':
                    racks_x[rack] = current_x
                    calibrated_shelf5_y = cur_y
                    log(f'Стойка {rack} X: OK = {current_x}, Y зафиксирован = {cur_y}')
                    break
                elif action == 'move':
                    cur_x, cur_y = do_move(runner, cur_x, cur_y, dx, dy)
                    current_x = cur_x
                    log(f'Стойка {rack} X: сдвиг dx={dx:+d} dy={dy:+d} → X={cur_x} Y={cur_y}')
                else:
                    print('  ? Примеры: ok, x+100, x-50, y+200, s, q')

        cal['racks']['1'] = racks_x[1]
        cal['racks']['2'] = racks_x[2]
        cal['racks']['3'] = racks_x[3]
        save_cal(cal)
        log(f'X стоек: rack1={racks_x[1]}, rack2={racks_x[2]}, rack3={racks_x[3]}')

        # ══════════════════════════════════════════
        # ФАЗА 2: Y-калибровка — каждая стойка отдельно
        # ══════════════════════════════════════════
        print('\n' + '='*60)
        print('  ФАЗА 2: Калибровка Y — КАЖДАЯ СТОЙКА ИМЕЕТ СВОИ АНКОРЫ')
        print(f'  Опорные полки: {ANCHOR_SHELVES}')
        print('='*60)
        log('=== ФАЗА 2: Y-калибровка (per-rack) ===')

        for rack in [1, 2, 3]:
            x_target = racks_x[rack]
            y_table = build_y_table_for_rack(cal, rack)

            print(f'\n{"="*60}')
            print(f'  СТОЙКА {rack} | X={x_target}')
            print(f'  (анкоры записываются только для этой стойки)')
            print('='*60)
            log(f'--- Стойка {rack} ---')

            cur_x, cur_y = do_move(runner, cur_x, cur_y, x_target - cur_x, 0)
            time.sleep(0.3)

            for shelf in ANCHOR_SHELVES:
                if is_disabled(cal, rack, shelf):
                    log(f'  [{rack}.{shelf}] заблокировано — пропуск')
                    continue

                y_target = y_table[shelf]
                log(f'  [{rack}.{shelf}] едем Y={y_target}')
                print(f'\n  Полка {shelf:2d} | текущий Y={y_target}')
                print(f'  Еду Y={y_target}...')

                cur_x, cur_y = do_move(runner, cur_x, cur_y, 0, y_target - cur_y)
                time.sleep(0.3)

                current_y = cur_y
                while True:
                    ans = ask(f'  [{rack}.{shelf}] X={cur_x} Y={current_y} → ')
                    action, dx, dy = parse_cmd(ans)

                    if action == 'quit':
                        raise KeyboardInterrupt
                    elif action == 'skip':
                        log(f'  [{rack}.{shelf}] пропущено')
                        break
                    elif action == 'ok':
                        # Записываем анкор ТОЛЬКО для этой стойки
                        update_rack_anchor(cal, rack, shelf, current_y)
                        y_table = build_y_table_for_rack(cal, rack)
                        # Если X сдвигался — обновляем racks_x чтобы следующие полки ехали к правильному X
                        if cur_x != racks_x[rack]:
                            racks_x[rack] = cur_x
                            cal['racks'][str(rack)] = cur_x
                            log(f'  [{rack}.{shelf}] X обновлён → {cur_x}')
                        log(f'  [{rack}.{shelf}] OK: Y={current_y} → rack{rack} anchor обновлён')
                        cur_y = current_y
                        break
                    elif action == 'move':
                        cur_x, cur_y = do_move(runner, cur_x, cur_y, dx, dy)
                        current_y = cur_y
                        log(f'  [{rack}.{shelf}] сдвиг dx={dx:+d} dy={dy:+d} → X={cur_x} Y={cur_y}')
                    else:
                        print('  ? Примеры: ok, y+100, y-50, x+50, s, q')

            # Сохраняем после каждой стойки
            save_cal(cal)

    except KeyboardInterrupt:
        print('\n\n  Прерывание — сохраняю прогресс...')
        save_cal(cal)
    finally:
        try:
            runner.close()
        except:
            pass

    # Итоговый отчёт
    print(f'\n{"="*60}')
    print('  ИТОГ КАЛИБРОВКИ:')
    print(f'  X стоек: rack1={racks_x[1]}, rack2={racks_x[2]}, rack3={racks_x[3]}')
    for rack in [1, 2, 3]:
        anchors = get_rack_anchors(cal, rack)
        print(f'\n  Стойка {rack} анкоры Y:')
        for a in sorted(anchors, key=lambda x: x['shelf']):
            print(f'    Полка {a["shelf"]:2d}: Y={a["front_y"]}')
    print(f'\n  Лог: {LOG_FILE}')
    # Сохраняем последнюю позицию каретки
    import json
    with open('/tmp/carriage_pos.json', 'w') as pf:
        json.dump({'x': cur_x, 'y': cur_y, 'address': 'calibrated'}, pf)
    log('=== Калибровка завершена ===')

if __name__ == '__main__':
    main()
