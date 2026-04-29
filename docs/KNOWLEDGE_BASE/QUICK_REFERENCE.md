# ⚡ QUICK REFERENCE — Шпаргалка команд BookCabinet

Все команды для быстрого копирования. Подробности → [SCRIPTS.md](SCRIPTS.md).

---

## 📍 Перемещение каретки (goto.py)

```bash
# Переместить каретку в ячейку с заданной скоростью
python3 ~/bookcabinet/tools/goto.py 800 1.1.5

# С хомингом перед перемещением (рекомендуется после включения)
python3 ~/bookcabinet/tools/goto.py --home 800 1.3.5

# Со скоростью 1500 шагов/сек
python3 ~/bookcabinet/tools/goto.py 1500 2.1.16
```

**Формат адреса:** `depth.rack.shelf` (например `2.1.16` = задний.стойка1.полка16)

**Скорость:** 100–10000 шагов/сек. Рекомендуемая рабочая: 800–2600.

---

## 📦 Операции с полочками (shelf_operations.py)

```bash
# Извлечь полочку из ПЕРЕДНЕГО ряда (depth=1)
python3 ~/bookcabinet/tools/shelf_operations.py extract_front

# Вернуть полочку в ПЕРЕДНИЙ ряд
python3 ~/bookcabinet/tools/shelf_operations.py return_front

# Извлечь полочку из ЗАДНЕГО ряда (depth=2)
python3 ~/bookcabinet/tools/shelf_operations.py extract_rear

# Вернуть полочку в ЗАДНИЙ ряд
python3 ~/bookcabinet/tools/shelf_operations.py return_rear

# Перекладка: из переднего ряда в задний (В ОДНОЙ ячейке)
python3 ~/bookcabinet/tools/shelf_operations.py front_to_rear

# Перекладка: из заднего ряда в передний (В ОДНОЙ ячейке)
python3 ~/bookcabinet/tools/shelf_operations.py rear_to_front
```

> ⚠️ Каретка должна уже стоять в нужной ячейке перед вызовом!

---

## 🪟 Шторки (shutter.py)

```bash
# Открыть внутреннюю шторку
python3 ~/bookcabinet/tools/shutter.py inner open

# Закрыть внешнюю шторку
python3 ~/bookcabinet/tools/shutter.py outer close

# Открыть обе шторки
python3 ~/bookcabinet/tools/shutter.py both open

# Узнать состояние обеих шторок
python3 ~/bookcabinet/tools/shutter.py both state

# Закрыть обе шторки (аварийный вариант)
python3 ~/bookcabinet/tools/shutter.py both close
```

**Пины:** inner = GPIO 3, outer = GPIO 2. HIGH=открыта, LOW=закрыта.

---

## 🏠 Хоминг

```bash
# XY хоминг через pigpio wave_chain (основной)
python3 ~/bookcabinet/tools/homing_pigpio.py

# Goto с хомингом перед перемещением
python3 ~/bookcabinet/tools/goto.py --home 1.3.5

# Goto с хомингом + кастомная скорость
python3 ~/bookcabinet/tools/goto.py --home 800 1.3.5
```

Хоминг движется к LEFT (X) и BOTTOM (Y) концевикам, затем отступает и фиксирует X=0, Y=0.

---

## 🚀 Полный старт системы

```bash
# Хоминг XY + калибровка лотка (делать после каждого включения)
python3 ~/bookcabinet/tools/startup_sequence.py
```

---

## 📤 Универсальная выдача книги (move_shelf.py)

```bash
# Взять полочку из ячейки 2.1.16 и отвезти в окно 1.2.9
# depth определяется автоматически по первой цифре адреса
python3 ~/bookcabinet/tools/move_shelf.py 2.1.16 1.2.9

# Со своей скоростью
python3 ~/bookcabinet/tools/move_shelf.py 2.1.16 1.2.9 1500

# С хомингом перед операцией
python3 ~/bookcabinet/tools/move_shelf.py --home 2.1.16 1.2.9
```

`move_shelf.py` — обёртка, которая автоматически:
1. Едет к `source_address`
2. Вызывает `extract_front` или `extract_rear` по depth
3. Едет к `target_address`
4. Вызывает `return_front` или `return_rear` по depth

---

## 🔄 Перенос полочки между ячейками (вручную)

```bash
# Пример: перенести из 1.3.5 (передний) в 2.1.10 (задний)
python3 ~/bookcabinet/tools/goto.py 800 1.3.5
python3 ~/bookcabinet/tools/shelf_operations.py extract_front

python3 ~/bookcabinet/tools/goto.py 800 2.1.10
python3 ~/bookcabinet/tools/shelf_operations.py return_rear
```

---

## 🔍 Диагностика

```bash
# Проверить концевики XY
python3 ~/bookcabinet/tools/test_sensors.py

# Проверить замки
python3 ~/bookcabinet/tools/test_locks.py

# Проверить шторки
python3 ~/bookcabinet/tools/test_shutters.py

# Проверить моторы XY
python3 ~/bookcabinet/tools/test_motors.py
```

---

## 📝 Примечания

| Параметр | Значение |
|----------|----------|
| Рекомендуемая скорость | 800–2600 шагов/сек |
| Жёсткий лимит скорости | 10000 шагов/сек |
| Окно выдачи | `1.2.9` |
| SSH | `admin42@2.56.241.126 -p 2222` |
| Позиция после хоминга | X=65 (rack1), Y зависит от полки |
