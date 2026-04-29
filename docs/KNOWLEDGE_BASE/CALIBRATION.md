# 📐 CALIBRATION.md — Калибровка BookCabinet

Описание формата `calibration.json` и процесса калибровки. Источник: `calibration.json`, `tools/calibration.py`, `tools/calibrate_all.py`.

---

## Формат calibration.json

Файл хранится в корне репо: `/home/admin42/bookcabinet/calibration.json`.

### Структура верхнего уровня

```json
{
  "version": "2026-04-27",
  "description": "BookCabinet XY calibration",
  "racks": { ... },
  "depth": { ... },
  "shelves": { ... },
  "disabled_cells": [...],
  "special_cells": { "window": "1.2.9" },
  "motion": { ... },
  "shutters": { ... },
  "locks": { ... },
  "tray": { ... }
}
```

### Секция `racks` — X-координаты стоек

```json
"racks": {
  "1": 65,
  "2": 10205,
  "3": 20360
}
```

X-позиции в шагах для каждой из 3 стоек.

### Секция `depth` — параметры глубины

```json
"depth": {
  "front": 1,
  "back": 2,
  "back_y_offset": 30
}
```

### Секция `shelves` — Y-анкоры полок

```json
"shelves": {
  "method": "piecewise_linear_per_depth",
  "rack_y_anchors": {
    "1": [
      { "shelf": 0,  "front_y": 60,    "back_y": 60 },
      { "shelf": 1,  "front_y": 2210,  "back_y": 2210 },
      { "shelf": 7,  "front_y": 14982, "back_y": 14982 },
      { "shelf": 21, "front_y": 45280, "back_y": 45280 }
    ],
    "2": [ ... ],
    "3": [ ... ]
  }
}
```

**Метод:** кусочно-линейная интерполяция между анкорами.

**Важно:** каждая стойка имеет **свои** Y-анкоры из-за неидеальной геометрии шкафа. Не усредняй!

### Пример: rack_y_anchors стойка 1

| shelf | front_y | Описание |
|-------|---------|----------|
| 0 | 60 | Нулевая полка |
| 1 | 2210 | Первая полка |
| 3 | 6445 | |
| 5 | 10740 | |
| 7 | 14982 | |
| 10 | 21380 | |
| 14 | 29900 | |
| 18 | 38443 | |
| 21 | 45280 | Последняя полка |

### Секция `tray` — параметры лотка

```json
"tray": {
  "total_steps": 22467,
  "center_steps": 11233,
  "freq_hz": 12000,
  "calibrated": "2026-04-27",
  "backoff_front": 1366,
  "backoff_back": 1445
}
```

### Секция `motion` — скорости

```json
"motion": {
  "fast_steps_per_sec": 3000,
  "homing_fast_steps_per_sec": 1800,
  "slow_steps_per_sec": 300,
  "wave_seg": 200
}
```

### Секция `locks` — состояние замков

```json
"locks": {
  "front": {
    "pin": 12,
    "status": "BROKEN - spins one direction only, needs replacement"
  },
  "back": {
    "pin": 13,
    "status": "OK - range 0-90 degrees"
  }
}
```

### Секция `disabled_cells` — отключённые ячейки

Ячейки, которые недоступны (конструктивно или по другим причинам):
```json
"disabled_cells": [
  "1.1.0", "1.1.10", "1.1.11", "1.1.21",
  "1.2.0", "1.2.7", "1.2.8", "1.2.10", "1.2.11",
  ...
]
```

---

## Процесс калибровки

### Полная последовательность с нуля

```bash
# Шаг 1: Хоминг XY
python3 ~/bookcabinet/tools/homing_pigpio.py

# Шаг 2: Калибровка лотка
python3 ~/bookcabinet/tools/tray_platform.py
# Запомнить: total_steps и center_steps → обновить calibration.json

# Шаг 3: Калибровка всех ячеек XY
python3 ~/bookcabinet/tools/calibrate_all.py
# Скорость по умолчанию: 2000 шагов/сек
# Интерактивно: оператор подтверждает или корректирует каждую позицию
```

### calibrate_all.py — интерактивный режим

```
Ячейка 1.1.1 → Каретка едет к предсказанной позиции
[Enter] — подтвердить
[W/A/S/D] — скорректировать позицию
[Q] — пропустить ячейку
```

Результат сохраняется в `calibration.json` в секцию `rack_y_anchors`.

### Калибровка только лотка

```bash
python3 ~/bookcabinet/tools/tray_platform.py
```

Лоток движется к переднему концевику, потом к заднему, замеряет расстояние. Результат усредняется по 2 прогонам.

### После калибровки

1. Убедиться что `calibration.json` обновился (`version` ← текущая дата)
2. Перезапустить сервис: `sudo systemctl restart bookcabinet`
3. Проверить доступность ячеек через веб-интерфейс

---

## Алгоритм resolve_cell

```python
from calibration import resolve_cell

x, y = resolve_cell("2.1.16")
```

### Алгоритм

1. Разобрать адрес: `depth=2, rack=1, shelf=16`
2. `x = racks[rack]` = 65 (для rack=1)
3. Найти в `rack_y_anchors[rack]` два ближайших анкора по shelf
4. Линейно интерполировать `y` между ними
5. Если `depth=2` — добавить `back_y_offset=30` (незначительно)
6. Вернуть `(x, y)`

### Пример

```
Адрес: 2.1.16
rack=1 → x=65
shelf=16 → между shelf=14 (y=29900) и shelf=18 (y=38443)
интерполяция: 14→16/14→18 = 2/4 = 0.5
y = 29900 + (38443-29900)*0.5 = 29900 + 4271 = 34171
+ back_y_offset 30 = 34201
```

---

## Заметки

- `back_y = front_y` для всех ячеек (отдельный offset не нужен — подтверждено измерениями)
- Стойки имеют независимые Y-анкоры из-за неидеальной геометрии
- После замены механических компонентов — перекалибровать affected стойку
- Полный перекалиб занимает ~2–3 часа
