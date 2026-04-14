# BookCabinet — Аппаратная карта

> Обновлено: 2026-04-14

## GPIO распиновка (BCM)

### Моторы XY (CoreXY)
| Функция | BCM Pin | Описание |
|---------|---------|----------|
| MOTOR_A_STEP | 14 | Мотор A — шаг |
| MOTOR_A_DIR | 15 | Мотор A — направление |
| MOTOR_B_STEP | 19 | Мотор B — шаг |
| MOTOR_B_DIR | 21 | Мотор B — направление |

### Мотор платформы (лоток)
| Функция | BCM Pin | Описание |
|---------|---------|----------|
| TRAY_STEP | 18 | CLK+ на драйвере |
| TRAY_DIR | 27 | DIR=0 → вперёд, DIR=1 → назад |
| TRAY_EN1 | 25 | Enable 1 — LOW для работы |
| TRAY_EN2 | 26 | Enable 2 — LOW для работы |

### Концевики платформы
| Функция | BCM Pin | Логика |
|---------|---------|--------|
| ENDSTOP_FRONT | 7 | 1 = нажат, 0 = свободен |
| ENDSTOP_BACK | 20 | 1 = нажат, 0 = свободен |

> Требуется pull-up: `pi.set_pull_up_down(pin, pigpio.PUD_UP)`

### Концевики каретки XY
| Функция | BCM Pin | Логика |
|---------|---------|--------|
| SENSOR_LEFT | 9 | HIGH = сработал |
| SENSOR_RIGHT | 10 | HIGH = сработал |
| SENSOR_BOTTOM | 8 | HIGH = сработал |
| SENSOR_TOP | 11 | HIGH = сработал |

> glitch filter обязателен на пинах 9, 10 (300 мкс)

### Сервоприводы замков (PWM 50 Гц)
| Функция | BCM Pin | Статус | Примечание |
|---------|---------|--------|------------|
| LOCK_FRONT | 12 | ❌ НЕИСПРАВЕН | Крутит только в одну сторону |
| LOCK_REAR | 13 | ✅ Работает | 0°=500us, 90°=1500us, 180°=2500us |

> Метод: `pi.set_servo_pulsewidth(pin, us)`
> После установки угла: `pi.set_servo_pulsewidth(pin, 0)` — отключить сигнал

### Шторки (реле)
| Функция | BCM Pin | Описание |
|---------|---------|----------|
| SHUTTER_OUTER | 2 | LOW=закрыта, HIGH=открыта (SDA1) |
| SHUTTER_INNER | 3 | LOW=закрыта, HIGH=открыта (SCL1) |

---

## Управление платформой

### Метод: pigpio wave (аппаратные импульсы)

Плавное движение без рывков. Python не участвует в генерации импульсов.

```python
import pigpio
import time

STEP = 18
DIR = 27
ENABLE1 = 25
ENABLE2 = 26
ENDSTOP_FRONT = 7
ENDSTOP_BACK = 20

FREQ = 12000  # Гц — оптимально для тишины и точности

pi = pigpio.pi()

# Настройка пинов
pi.set_mode(STEP, pigpio.OUTPUT)
pi.set_mode(DIR, pigpio.OUTPUT)
pi.set_mode(ENABLE1, pigpio.OUTPUT)
pi.set_mode(ENABLE2, pigpio.OUTPUT)
pi.set_mode(ENDSTOP_FRONT, pigpio.INPUT)
pi.set_mode(ENDSTOP_BACK, pigpio.INPUT)
pi.set_pull_up_down(ENDSTOP_FRONT, pigpio.PUD_UP)
pi.set_pull_up_down(ENDSTOP_BACK, pigpio.PUD_UP)

# Включить драйвер
pi.write(ENABLE1, 0)
pi.write(ENABLE2, 0)

# Создать волну
period_us = int(1000000 / FREQ)
pulse_us = period_us // 2

pi.wave_clear()
waveform = [
    pigpio.pulse(1 << STEP, 0, pulse_us),
    pigpio.pulse(0, 1 << STEP, pulse_us)
]
pi.wave_add_generic(waveform)
wave_id = pi.wave_create()

# Движение до концевика
def move_until_endstop(direction, endstop_pin, max_time=10):
    pi.write(DIR, direction)  # 0=вперёд, 1=назад
    time.sleep(0.01)
    
    pi.wave_send_repeat(wave_id)
    
    start = time.time()
    while pi.read(endstop_pin) == 0 and (time.time() - start) < max_time:
        time.sleep(0.0005)
    
    pi.wave_tx_stop()
    elapsed = time.time() - start
    steps = int(elapsed * FREQ)
    reached = pi.read(endstop_pin) == 1
    return steps, reached

# Пример: калибровка
pi.write(DIR, 0)  # вперёд
steps_front, _ = move_until_endstop(0, ENDSTOP_FRONT)
steps_total, _ = move_until_endstop(1, ENDSTOP_BACK)
middle = steps_total // 2

# Выключить
pi.wave_delete(wave_id)
pi.write(ENABLE1, 1)
pi.write(ENABLE2, 1)
pi.stop()
```

### Калиброванные параметры (2026-04-14)

| Параметр | Значение |
|----------|----------|
| Частота | 12000 Гц |
| Полный ход | 21011 шагов |
| Центр | 10505 шагов |
| DIR=0 | Вперёд (к FRONT) |
| DIR=1 | Назад (к BACK) |

### Почему wave, а не bit-bang?

| Метод | Плюсы | Минусы |
|-------|-------|--------|
| time.sleep() | Простой | Рывки, неточность, шум |
| pigpio wave | Плавно, тихо, точно | Сложнее код |

---

## Управление замками (SG90)

### Метод: pigpio servo PWM

```python
import pigpio
import time

LOCK_PIN = 13  # Замок 2 (рабочий)

pi = pigpio.pi()

# Открыть (0°)
pi.set_servo_pulsewidth(LOCK_PIN, 500)
time.sleep(1)

# Закрыть (90°)
pi.set_servo_pulsewidth(LOCK_PIN, 1500)
time.sleep(1)

# Отключить сигнал (чтобы не жужжала)
pi.set_servo_pulsewidth(LOCK_PIN, 0)

pi.stop()
```

### Диапазон SG90

| Угол | Pulsewidth |
|------|------------|
| 0° | 500 мкс |
| 45° | 1000 мкс |
| 90° | 1500 мкс |
| 135° | 2000 мкс |
| 180° | 2500 мкс |

---

## Хоминг каретки XY

См. `tools/corexy_pigpio.py`

- Метод: wave_chain + callback + wave_tx_stop()
- Скорости: FAST=1500, SLOW=400 (>3000 = stall)
- glitch filter: 300μs на пинах 9, 10

---

## Известные проблемы

1. **Замок 1 (GPIO 12)** — неисправен, крутит только в одну сторону
2. **Концевик BACK (GPIO 20)** — возможен дребезг, использовать debounce
3. **Шторки (GPIO 2, 3)** — GPIO.cleanup() откроет шторки, нужен daemon или pull-down

