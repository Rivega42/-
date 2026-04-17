# Операции с полочками BookCabinet

## Общая концепция

Шкаф имеет **два ряда** полочек:
- **Передний ряд (depth=1)** — ближе к пользователю, работает только передний замок
- **Задний ряд (depth=2)** — дальше, требует перехват между замками

**Точка перехвата** — позиция, где замок находится на середине каретки и может зацепить/отпустить полочку.

---

## Задний ряд (depth=2)

### Выдвижение полочки

```
1. Платформа → BACK концевик
2. Задний замок → 1200 (захват) + pigs s 13 0
3. Платформа → точка перехвата заднего замка (~17000 шагов к FRONT)
4. Задний замок → 500 (отпустить) + pigs s 13 0
5. Платформа → точка перехвата переднего замка (+12800 к BACK)
6. Передний замок → 1200 (захват) + pigs s 12 0
7. Платформа → полный выезд (~18800 к FRONT, полочка на каретке)
```

### Возврат полочки

```
1. Передний замок → 1200 (держит полочку) + pigs s 12 0
2. Платформа → точка перехвата переднего замка (+12800 к BACK)
3. Передний замок → 500 (отпустить) + pigs s 12 0
4. Платформа → точка перехвата заднего замка (+12800 к FRONT)
5. Задний замок → 1200 (захват) + pigs s 13 0
6. Платформа → BACK концевик
7. Задний замок → 500 (отпустить) + pigs s 13 0
8. Платформа → центр
```

---

## Передний ряд (depth=1)

### Выдвижение полочки

```
1. Платформа → FRONT концевик
2. Передний замок → 1200 (захват) + pigs s 12 0
3. Платформа → точка перехвата переднего замка (~4500 шагов к BACK)
4. Передний замок → 500 (отпустить) + pigs s 12 0
   — полочка остаётся на каретке
```

### Возврат полочки

```
1. Передний замок → 1200 (держит полочку) + pigs s 12 0
2. Платформа → FRONT концевик
3. Передний замок → 500 (отпустить) + pigs s 12 0
   — полочка остаётся в ячейке
4. Платформа → центр
```

---

## Константы

```python
# Платформа
TRAY_TOTAL = 21500
TRAY_CENTER = 10750
LOCK_DISTANCE = 12800      # Расстояние между замками

# Точки перехвата (от соответствующего концевика)
HANDOFF_FROM_FRONT = 4500  # Передний замок на середине каретки
HANDOFF_FROM_BACK = 4500   # Задний замок на середине каретки

# Полный выезд (от точки перехвата к FRONT)
FULL_EXTEND = 18800        # Шагов к FRONT чтобы полочка легла на каретку

# Замки
LOCK_GRAB = 1200           # Угол захвата (~70°)
LOCK_RELEASE = 500         # Угол отпускания (0°)

# GPIO
LOCK_FRONT = 12
LOCK_BACK = 13
```

---

## Важные правила

1. **После каждой команды серво** — отключать PWM:
   ```bash
   pigs s 13 1200 && sleep 0.5 && pigs s 13 0
   ```

2. **Не ехать в нажатый концевик** — проверять перед движением

3. **Калибровка только при хоминге** — не каждый цикл работы с полочкой

4. **Использовать wave_chain** — не wave_send_once в цикле!

---

## Полный цикл (пример кода)

```python
def lock_grab(pin):
    """Захватить замком"""
    os.system(f"pigs s {pin} 1200")
    time.sleep(0.5)
    os.system(f"pigs s {pin} 0")

def lock_release(pin):
    """Отпустить замок"""
    os.system(f"pigs s {pin} 500")
    time.sleep(0.5)
    os.system(f"pigs s {pin} 0")

def extract_back_shelf():
    """Выдвинуть полочку из заднего ряда"""
    tray_to_endstop(BACK)
    lock_grab(LOCK_BACK)
    tray_move(17000, direction=FRONT)
    lock_release(LOCK_BACK)
    tray_move(LOCK_DISTANCE, direction=BACK)
    lock_grab(LOCK_FRONT)
    tray_move(FULL_EXTEND, direction=FRONT)

def return_back_shelf():
    """Вернуть полочку в задний ряд"""
    lock_grab(LOCK_FRONT)
    tray_move(LOCK_DISTANCE, direction=BACK)
    lock_release(LOCK_FRONT)
    tray_move(LOCK_DISTANCE, direction=FRONT)
    lock_grab(LOCK_BACK)
    tray_to_endstop(BACK)
    lock_release(LOCK_BACK)
    tray_to_center()

def extract_front_shelf():
    """Выдвинуть полочку из переднего ряда"""
    tray_to_endstop(FRONT)
    lock_grab(LOCK_FRONT)
    tray_move(HANDOFF_FROM_FRONT, direction=BACK)
    lock_release(LOCK_FRONT)

def return_front_shelf():
    """Вернуть полочку в передний ряд"""
    lock_grab(LOCK_FRONT)
    tray_to_endstop(FRONT)
    lock_release(LOCK_FRONT)
    tray_to_center()
```
