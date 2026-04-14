# BookCabinet — Аппаратная карта

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
| TRAY_STEP | 18 | Шаг |
| TRAY_DIR | 27 | Направление. 0=вперед (FRONT), 1=назад (BACK) |
| TRAY_EN1 | 25 | Enable 1. LOW=работа, HIGH=отключен |
| TRAY_EN2 | 26 | Enable 2. LOW=работа, HIGH=отключен |

### Концевики XY
| Функция | BCM Pin | Логика |
|---------|---------|--------|
| LEFT | 9 | 1=нажат, 0=свободен |
| RIGHT | 10 | 1=нажат, 0=свободен |
| BOTTOM | 8 | 1=нажат, 0=свободен |
| TOP | 11 | 1=нажат, 0=свободен |

### Концевики платформы
| Функция | BCM Pin | Логика |
|---------|---------|--------|
| FRONT | 7 | 1=нажат, 0=свободен |
| BACK | 20 | 1=нажат, 0=свободен |

### Шторки (реле)
| Функция | BCM Pin | Логика |
|---------|---------|--------|
| SHUTTER_OUTER | 2 | HIGH=открыта, LOW=закрыта (SDA1) |
| SHUTTER_INNER | 3 | HIGH=открыта, LOW=закрыта (SCL1) |

**ВАЖНО:** Использовать через bookcabinet.hardware.gpio_manager, не напрямую!

### Замки (сервоприводы SG90)
| Функция | BCM Pin | Статус |
|---------|---------|--------|
| LOCK_FRONT | 12 | НЕИСПРАВЕН — крутит только в одну сторону |
| LOCK_BACK | 13 | Работает, диапазон 0-90 градусов |

---

## Калибровка платформы

- **Метод:** pigpio wave (аппаратные импульсы)
- **Частота:** 12000 Гц
- **Total travel:** ~21000 шагов
- **Center:** ~10500 шагов
- **DIR:** 0=вперед (к FRONT), 1=назад (к BACK)

---

## Хоминг XY

- **HOME позиция:** LEFT + BOTTOM (0,0)
- **Скорость FAST:** 800 шаг/сек
- **Скорость SLOW:** 300 шаг/сек
- **Glitch filter:** 300us на всех концевиках

### CoreXY направления
| Движение | A_DIR | B_DIR |
|----------|-------|-------|
| Вправо | 1 | 1 |
| Влево | 0 | 0 |
| Вверх | 1 | 0 |
| Вниз | 0 | 1 |

---

## Startup Sequence

Файл: tools/startup_sequence.py

1. **XY Homing** - LEFT + BOTTOM
2. **Tray Calibration** - FRONT - BACK - CENTER

Калибровка платформы выполняется ТОЛЬКО после успешного хоминга XY!

---

## Управление шторками

```python
from bookcabinet.hardware.gpio_manager import gpio
from bookcabinet.config import GPIO_PINS

# Открыть
gpio.write(GPIO_PINS['SHUTTER_OUTER'], 1)
gpio.write(GPIO_PINS['SHUTTER_INNER'], 1)

# Закрыть
gpio.write(GPIO_PINS['SHUTTER_OUTER'], 0)
gpio.write(GPIO_PINS['SHUTTER_INNER'], 0)
```

---

## Файлы

- bookcabinet/config.py — GPIO_PINS (источник истины)
- bookcabinet/hardware/shutters.py — управление шторками
- bookcabinet/hardware/gpio_manager.py — абстракция GPIO
- tools/startup_sequence.py — хоминг + калибровка
- tools/corexy_motion_v2.py — движение XY
- calibration.json — координаты стоек/полок
