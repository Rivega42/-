# Управление моторами BookCabinet

## Правильный способ управления

**ВАЖНО:** Использовать `wave_chain` с callback, а НЕ `wave_send_once` в цикле!

### Почему wave_send_once в цикле — плохо:
- Создаёт рваный сигнал между итерациями
- Моторы дребезжат
- Пропуск шагов под нагрузкой

### Правильно — wave_chain:
```python
import pigpio

pi = pigpio.pi()

# Создаём волну один раз
pi.wave_clear()
pulses = []
for _ in range(1000):  # большой блок
    pulses.append(pigpio.pulse(1 << STEP_PIN, 0, delay))
    pulses.append(pigpio.pulse(0, 1 << STEP_PIN, delay))
pi.wave_add_generic(pulses)
wid = pi.wave_create()

# Запускаем chain с повторением
chain = [255, 0, wid, 255, 1, repeat_low, repeat_high]
pi.wave_chain(chain)

# Ждём завершения или прерываем по концевику
while pi.wave_tx_busy():
    if pi.read(ENDSTOP) == 1:
        pi.wave_tx_stop()  # Мгновенная остановка!
        break
    time.sleep(0.001)
```

### Готовые скрипты
- **CoreXY хоминг:** `tools/corexy_pigpio.py`
- **Платформа:** использовать тот же подход с wave_chain

## Параметры драйвера TB6600

### Для NEMA17 (17HS4023):
- **Ток:** 1.9A (S4=OFF, S5=ON, S6=ON)
- **Микрошаг:** 8 (S1=ON, S2=OFF, S3=OFF) — компромисс момент/плавность

### Скорости:
- Быстрое движение: 4-8 kHz (delay 60-125 μs)
- Медленное (хоминг): 2-4 kHz (delay 125-250 μs)
- **НЕ использовать** >12 kHz под нагрузкой!

## GPIO пины

### Платформа (Tray):
- STEP: GPIO 18
- DIR: GPIO 27
- EN1: GPIO 25 (LOW = enabled)
- EN2: GPIO 26 (LOW = enabled)
- FRONT концевик: GPIO 7
- BACK концевик: GPIO 20

### CoreXY (каретка):
- Мотор A: STEP=14, DIR=15
- Мотор B: STEP=19, DIR=21
- LEFT: GPIO 9
- RIGHT: GPIO 10
- BOTTOM: GPIO 8
- TOP: GPIO 11

### Направления CoreXY:
| Движение | DIR_A | DIR_B |
|----------|-------|-------|
| Вправо   | 1     | 1     |
| Влево    | 0     | 0     |
| Вверх    | 1     | 0     |
| Вниз     | 0     | 1     |

### Направления платформы:
| Движение | DIR |
|----------|-----|
| К FRONT  | 0   |
| К BACK   | 1   |

## Замки (сервоприводы)

- Передний: GPIO 12
- Задний: GPIO 13

### Управление:
```bash
pigs s 13 1200   # Захват (~70°)
sleep 0.5
pigs s 13 0      # Отключить PWM (важно — убирает дребезг!)

pigs s 13 500    # Отпустить (0°)
sleep 0.5
pigs s 13 0      # Отключить PWM
```

**ВАЖНО:** Всегда отключать PWM после установки угла (`pigs s XX 0`), иначе серва дребезжит!

## Калибровочные константы

```python
TRAY_TOTAL = 21500        # Полный ход платформы (шаги)
TRAY_CENTER = 10750       # Центр
LOCK_DISTANCE = 12800     # Расстояние между замками
HANDOFF_OFFSET = 6400     # Смещение точки перехвата от центра
```
