#!/usr/bin/env python3
"""
calibrate.py — полная калибровка X стоек и Y полок.

Фаза 1: X-калибровка 3 стоек (на полке 5)
Фаза 2: Y-калибровка опорных полок (1,3,5,7,10,14,18,21) в каждой стойке
        Остальные полки — линейная интерполяция между опорами.

Управление в каждой точке:
  Enter      — OK, позиция верна
  x+100      — сдвиг по X на +100 шагов
  x-50       — сдвиг по X на -50 шагов
  y+200      — сдвиг по Y на +200 шагов
  y-100      — сдвиг по Y на -100 шагов
  s          — пропустить точку
  q          — выход (с сохранением того что есть)

Лог пишется в /tmp/calibration_log.txt
"""
import sys, os, json, time, datetime

sys.path.insert(0, '/home/admin42/bookcabinet/tools')
from book_sequences import BookSequenceRunner, XY_CONFIG

CAL_FILE = '/home/admin42/bookcabinet/calibration.json'
LOG_FILE = '/tmp/calibration_log.txt'

# Опорные полки для Y-калибровки
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

def build_y_table(cal):
    """Строим полную таблицу Y[0..21] из анкоров с интерполяцией."""
    anchors = cal['shelves']['anchors']
    anchor_map = {a['shelf']: a['front_y'] for a in anchors}
    keys = sorted(anchor_map.keys())
    result = {}
    for s in range(22):
        if s in anchor_map:
            result[s] = anchor_map[s]
        else:
            for i in range(len(keys)-1):
                s0, s1 = keys[i], keys[i+1]
                if s0 <= s <= s1:
                    t = (s - s0) / (s1 - s0)
                    result[s] = int(anchor_map[s0] + t*(anchor_map[s1]-anchor_map[s0]))
                    break
    return result

def update_anchors(cal, shelf, new_y):
    """Добавить или обновить анкор для полки."""
    anchors = cal['shelves']['anchors']
    for a in anchors:
        if a['shelf'] == shelf:
            a['front_y'] = new_y
            a['back_y'] = new_y
            return
    anchors.append({'shelf': shelf, 'front_y': new_y, 'back_y': new_y})
    anchors.sort(key=lambda a: a['shelf'])

def is_disabled(cal, rack, shelf):
    """Проверяем хотя бы один из depth=1 или depth=2 активен."""
    d1 = f'1.{rack}.{shelf}' not in cal['disabled_cells']
    d2 = f'2.{rack}.{shelf}' not in cal['disabled_cells']
    win = f'1.{rack}.{shelf}' == cal['special_cells'].get('window')
    return not (d1 or d2) or win

def parse_cmd(ans):
    """
    Парсим команду. Возвращаем ('ok'|'skip'|'quit'|'move', dx, dy).
    Форматы: '', 'ok' -> OK
             'x+100', 'x-50' -> move X
             'y+200', 'y-100' -> move Y
             'x+100 y-50' -> move X и Y
             's' -> skip
             'q' -> quit
    """
    ans = ans.strip().lower()
    if ans in ('', 'ok'):
        return 'ok', 0, 0
    if ans == 's':
        return 'skip', 0, 0
    if ans == 'q':
        return 'quit', 0, 0

    dx, dy = 0, 0
    import re
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
    """Двигаем каретку на delta от текущей позиции."""
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

def move_to_absolute(runner, cur_x, cur_y, target_x, target_y):
    """Переезд в абсолютную позицию через дельты."""
    dx = target_x - cur_x
    dy = target_y - cur_y
    new_x, new_y = do_move(runner, cur_x, cur_y, dx, dy)
    return new_x, new_y

def main():
    cal = load_cal()
    racks_x = {1: int(cal['racks']['1']),
               2: int(cal['racks']['2']),
               3: int(cal['racks']['3'])}
    y_table = build_y_table(cal)

    # Открываем лог
    with open(LOG_FILE, 'w') as f:
        f.write(f'=== Калибровка {datetime.datetime.now()} ===\n')

    print('\n' + '='*60)
    print('  КАЛИБРОВКА BookCabinet')
    print('  Фаза 1: X стоек (3 точки на полке 5)')
    print('  Фаза 2: Y опорных полок (8 точек × 3 стойки = 24)')
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
    runner._init_motion()  # инициализируем motion сразу
    cur_x, cur_y = 0, 0

    try:
        # ══════════════════════════════════════════
        # ФАЗА 1: X-калибровка стоек
        # ══════════════════════════════════════════
        print('\n' + '='*60)
        print('  ФАЗА 1: Калибровка X стоек')
        print('  Каретка будет вставать напротив каждой стойки на полке 5')
        print('='*60)
        log('=== ФАЗА 1: X-калибровка ===')

        # calibrated_y_for_shelf5 — общий Y для полки 5, уточняется на стойке 1
        # и переиспользуется для стоек 2 и 3
        shelf5_y = y_table[5]
        calibrated_shelf5_y = shelf5_y  # будет обновлён после стойки 1

        for rack in [1, 2, 3]:
            x_target = racks_x[rack]
            # Используем уже откалиброванный Y от предыдущей стойки
            target_y = calibrated_shelf5_y
            log(f'Стойка {rack}: едем X={x_target}, Y={target_y}')
            print(f'\n--- Стойка {rack} ---')
            print(f'  Еду X={x_target}, Y={target_y}...')

            # Едем к стойке дельтами от текущей позиции (без хоминга)
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
                    # Сохраняем откалиброванный Y — будет стартовым для следующей стойки
                    calibrated_shelf5_y = cur_y
                    log(f'Стойка {rack} X: OK = {current_x}, Y зафиксирован = {cur_y}')
                    break
                elif action == 'move':
                    cur_x, cur_y = do_move(runner, cur_x, cur_y, dx, dy)
                    current_x = cur_x
                    log(f'Стойка {rack} X: сдвиг dx={dx:+d} dy={dy:+d} → X={cur_x} Y={cur_y}')
                else:
                    print('  ? Примеры: ok, x+100, x-50, y+200, x+100 y-50, s, q')

        # Сохраняем X стоек
        cal['racks']['1'] = racks_x[1]
        cal['racks']['2'] = racks_x[2]
        cal['racks']['3'] = racks_x[3]
        save_cal(cal)
        log(f'X стоек: rack1={racks_x[1]}, rack2={racks_x[2]}, rack3={racks_x[3]}')

        # ══════════════════════════════════════════
        # ФАЗА 2: Y-калибровка опорных полок
        # ══════════════════════════════════════════
        print('\n' + '='*60)
        print(f'  ФАЗА 2: Калибровка Y опорных полок')
        print(f'  Опорные полки: {ANCHOR_SHELVES}')
        print(f'  Порядок: Стойка 1 → все опоры, Стойка 2 → все опоры, ...')
        print('='*60)
        log('=== ФАЗА 2: Y-калибровка ===')

        # Пересчитываем y_table с учётом новых анкоров
        y_table = build_y_table(cal)

        # calibrated_y_per_shelf: общий словарь откалиброванных Y
        # Заполняется на стойке 1, используется как старт для стоек 2 и 3
        calibrated_y_per_shelf = {}  # shelf -> Y

        for rack in [1, 2, 3]:
            x_target = racks_x[rack]
            print(f'\n{"="*60}')
            print(f'  СТОЙКА {rack} | X={x_target}')
            log(f'--- Стойка {rack} ---')

            # Едем к X стойки дельтой от текущей позиции
            cur_x, cur_y = do_move(runner, cur_x, cur_y, x_target - cur_x, 0)
            time.sleep(0.3)

            for shelf in ANCHOR_SHELVES:
                if is_disabled(cal, rack, shelf):
                    log(f'  [{rack}.{shelf}] заблокировано — пропуск')
                    continue

                # Используем уже откалиброванный Y если есть, иначе из таблицы
                y_target = calibrated_y_per_shelf.get(shelf, y_table[shelf])
                log(f'  [{rack}.{shelf}] едем Y={y_target}')
                print(f'\n  Полка {shelf:2d} | Y={y_target}')
                print(f'  Еду Y={y_target}...')

                # Движение только по Y дельтой
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
                        # Обновляем анкор
                        update_anchors(cal, shelf, current_y)
                        y_table = build_y_table(cal)  # пересчёт интерполяции
                        # Запоминаем откалиброванный Y для следующих стоек
                        calibrated_y_per_shelf[shelf] = current_y
                        log(f'  [{rack}.{shelf}] OK: Y={current_y} (зафиксирован для всех стоек)')
                        cur_y = current_y
                        break
                    elif action == 'move':
                        cur_x, cur_y = do_move(runner, cur_x, cur_y, dx, dy)
                        current_y = cur_y
                        log(f'  [{rack}.{shelf}] сдвиг dx={dx:+d} dy={dy:+d} → X={cur_x} Y={cur_y}')
                    else:
                        print('  ? Примеры: ok, y+100, y-50, x+50, s, q')

        # Финальное сохранение
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
    print(f'\n  Анкоры Y:')
    for a in sorted(cal['shelves']['anchors'], key=lambda x: x['shelf']):
        print(f'    Полка {a["shelf"]:2d}: Y={a["front_y"]}')
    print(f'\n  Лог: {LOG_FILE}')
    log('=== Калибровка завершена ===')

if __name__ == '__main__':
    main()
