# 📜 SCRIPTS.md — Описание скриптов BookCabinet

Все скрипты живут в `~/bookcabinet/tools/`.

Быстрые примеры → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

---

## goto.py — перемещение каретки XY

### Назначение
Переместить каретку CoreXY в указанную ячейку шкафа. Адрес ячейки разрешается через `calibration.py` → координаты XY в шагах.

### Использование

```bash
python3 goto.py <speed> <address>
python3 goto.py --home <speed> <address>
python3 goto.py --home <address>          # скорость по умолчанию
```

### Параметры

| Параметр | Описание |
|----------|----------|
| `speed` | Скорость в шагах/сек. Диапазон: 100–10000. Рекомендуем 800–2600. |
| `address` | Адрес ячейки в формате `depth.rack.shelf` (например `2.1.16`) |
| `--home` | Выполнить хоминг XY перед перемещением |

### Файл состояния

После каждого перемещения координаты сохраняются в:
```
/tmp/carriage_pos.json
```
Формат:
```json
{"x": 65, "y": 14982, "address": "1.1.7"}
```

### Скоростные режимы

| Режим | Диапазон | Использование |
|-------|----------|---------------|
| SLOW | 300 | Хоминг (slow phase), ручная коррекция |
| NORMAL | 800–2600 | Рабочие перемещения |
| FAST | 3000+ | Только если откалибровано и проверено |
| HARD LIMIT | 10000 | Абсолютный максимум, не использовать в prod |

---

## shelf_operations.py — операции с полочками

### Назначение
Управление лотком (tray) и замками (servo locks) для извлечения и возврата полочек. Поддерживает 6 команд.

### Команды

| Команда | Описание |
|---------|----------|
| `extract_front` | Извлечь полочку из переднего ряда (depth=1) |
| `return_front` | Вернуть полочку в передний ряд |
| `extract_rear` | Извлечь полочку из заднего ряда (depth=2) |
| `return_rear` | Вернуть полочку в задний ряд |
| `front_to_rear` | Переложить из переднего в задний В ОДНОЙ ЯЧЕЙКЕ |
| `rear_to_front` | Переложить из заднего в передний В ОДНОЙ ЯЧЕЙКЕ |

### Ключевые константы (откалибровано 21.04.2026)

```python
TRAY_CENTER = 11300          # центральная позиция лотка (шаги)
TRAY_FREQ = 12000            # частота шагов (Hz)

# Задний ряд (depth=2)
REAR_HANDOFF_REAR_FROM_BACK = 16800   # задний замок захватывает на отходе назад
REAR_HANDOFF_FRONT_FROM_BACK = 4200   # передний замок захватывает на отходе назад

# Передний ряд (depth=1)
FRONT_HANDOFF_FRONT_FROM_BACK = 5700  # передний замок
FRONT_HANDOFF_REAR_FROM_BACK = 18300  # задний замок
LOCK_DISTANCE = 12600                  # расстояние между точками перехвата
```

### Замки: PWM значения

```python
LOCK_GRAB_PWM = 1200    # μs — захват (примерно 90°)
LOCK_RELEASE_PWM = 500  # μs — отпустить (примерно 0°)
```

> Подробная логика замков → [SHELF_OPERATIONS.md](SHELF_OPERATIONS.md)

---

## shutter.py — управление шторками

### Назначение
Standalone скрипт управления шторками через GPIO (реле). Используется как из командной строки, так и импортом в workflow.

### Использование

```bash
python3 shutter.py <target> <action>
# target: inner | outer | both
# action: open | close | state
```

### GPIO

| Шторка | Пин | HIGH | LOW |
|--------|-----|------|-----|
| outer (внешняя) | GPIO 2 (SDA1) | открыта | закрыта |
| inner (внутренняя) | GPIO 3 (SCL1) | открыта | закрыта |

### Время хода шторки

Физически шторка движется ~10 секунд. В коде используется таймаут **15 секунд** для запаса.

---

## move_shelf.py — универсальная выдача (новый)

### Назначение
Обёртка высокого уровня: берёт полочку из source_address и отвозит в target_address с автоматическим определением depth.

### Использование

```bash
python3 move_shelf.py <source> <target>
python3 move_shelf.py <source> <target> <speed>
python3 move_shelf.py --home <source> <target>
```

### Алгоритм

1. Определить depth из первой цифры `source_address` (1=front, 2=rear)
2. `goto(source_address, speed)`
3. Вызвать `extract_front` или `extract_rear` по depth
4. `goto(target_address, speed)`
5. Определить depth из `target_address`
6. Вызвать `return_front` или `return_rear`

### Override флаги

```bash
# Принудительно использовать extract_rear независимо от адреса
python3 move_shelf.py --force-rear 1.2.9 2.1.16

# Принудительно return_front
python3 move_shelf.py --force-front 2.1.16 1.2.9
```

---

## homing_pigpio.py — XY хоминг

### Назначение
Хоминг каретки CoreXY через pigpio wave_chain. Движется к концевикам LEFT (X) и BOTTOM (Y).

### Последовательность

1. Быстрый подход к LEFT концевику (скорость HOMING_FAST=1800)
2. Отступить на backoff
3. Медленный подход к LEFT (скорость SLOW=300)
4. Зафиксировать X=0
5. Аналогично для BOTTOM → Y=0
6. Переехать на X=65 (rack1 anchor) во избежание столкновения

### Концевики хоминга

```
SENSOR_LEFT=9 (для X), SENSOR_BOTTOM=8 (для Y)
Активный уровень: HIGH (1 = нажат)
```

---

## startup_sequence.py — полный старт

### Назначение
Выполняет полную последовательность инициализации шкафа после включения.

### Последовательность

1. XY хоминг (`homing_pigpio`)
2. Закрыть обе шторки
3. Откалибровать лоток (tray calibration): движение к переднему, потом заднему концевику → определить total_steps и center

---

## calibrate.py / calibrate_all.py — калибровка XY

### calibrate.py
Интерактивная ручная калибровка одной ячейки. Оператор подтверждает каждую позицию.

### calibrate_all.py
Автоматический обход всех ячеек. Каретка едет к каждой ячейке на скорости 2000, оператор может корректировать позиции.

```bash
python3 calibrate_all.py    # интерактивно, обходит все ячейки
```

Результат сохраняется в `calibration.json`.

---

## calibration.py — модуль разрешения адресов

### Назначение
Библиотечный модуль. Разрешает адрес ячейки `depth.rack.shelf` в физические координаты XY (шаги).

### Ключевая функция

```python
from calibration import resolve_cell

x, y = resolve_cell("2.1.16")
# x = 65 (rack1 anchor)
# y = интерполировано по rack_y_anchors[rack][shelf]
```

### Формат calibration.json

Подробно → [CALIBRATION.md](CALIBRATION.md)

### get_window_cell()

```python
from calibration import get_window_cell
window = get_window_cell()  # → "1.2.9"
```

---

## tray_platform.py — калибровка лотка

Определяет `total_steps` и `center_steps` лотка. Используется для обновления `calibration.json`.

Результат: total=22467, center=11233, freq=12000Hz (откалибровано 2026-04-27).

---

## Остальные скрипты

| Скрипт | Назначение |
|--------|------------|
| `test_sensors.py` | Проверить все концевики |
| `test_locks.py` | Проверить замки (servo PWM) |
| `test_shutters.py` | Проверить шторки (GPIO реле) |
| `test_motors.py` | Тест моторов XY |
| `corexy_pigpio.py` | Базовый модуль движения CoreXY через pigpio |
| `homing.py` | Устаревший хоминг (заменён homing_pigpio.py) |
| `measure_bounds.py` | Измерить физические границы XY |
