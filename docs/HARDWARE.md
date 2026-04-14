# BookCabinet — Аппаратная карта

**Источник истины:** `bookcabinet/config.py`

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
| TRAY_DIR | 27 | Направление: 0=вперед (FRONT), 1=назад (BACK) |
| TRAY_EN1 | 25 | Enable 1: LOW=работа, HIGH=отключен |
| TRAY_EN2 | 26 | Enable 2: LOW=работа, HIGH=отключен |

**Файл управления:** `tools/tray_platform.py`

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
| SHUTTER_OUTER | 2 | HIGH=открыта, LOW=закрыта |
| SHUTTER_INNER | 3 | HIGH=открыта, LOW=закрыта |

**ВАЖНО:** Использовать через `bookcabinet.hardware.gpio_manager`!

### Замки (сервоприводы SG90)
| Функция | BCM Pin | Статус |
|---------|---------|--------|
| LOCK_FRONT | 12 | НЕИСПРАВЕН |
| LOCK_BACK | 13 | НЕИСПРАВЕН (колбасит) |

---

## Калибровка платформы

**Файл:** `tools/tray_platform.py`

```bash
python3 tools/tray_platform.py calibrate  # Полная калибровка
python3 tools/tray_platform.py status     # Состояние концевиков
python3 tools/tray_platform.py front      # Двигать к FRONT
python3 tools/tray_platform.py back       # Двигать к BACK
```

**Параметры:**
- Частота: 12000 Hz (оптимум тишины и надежности)
- Total travel: ~21000 шагов
- Center: ~10500 шагов
- Метод: pigpio wave (аппаратные импульсы)

---

## Хоминг XY

**Файл:** `tools/corexy_motion_v2.py`

```bash
python3 tools/corexy_motion_v2.py home     # Хоминг к LEFT + BOTTOM
python3 tools/corexy_motion_v2.py x-sweep  # Тест X оси
python3 tools/corexy_motion_v2.py y-sweep  # Тест Y оси
```

**Параметры:**
- HOME позиция: LEFT + BOTTOM (0,0)
- Скорость FAST: 800 шаг/сек
- Скорость SLOW: 300 шаг/сек
- Glitch filter: 300us на всех концевиках

### CoreXY направления
| Движение | A_DIR | B_DIR |
|----------|-------|-------|
| Вправо | 1 | 1 |
| Влево | 0 | 0 |
| Вверх | 1 | 0 |
| Вниз | 0 | 1 |

---

## Startup Sequence

**Файл:** `tools/startup_sequence.py`

1. XY Homing -> LEFT + BOTTOM
2. Tray Calibration -> FRONT -> BACK -> CENTER

**ВАЖНО:** Калибровка платформы выполняется ТОЛЬКО после успешного хоминга XY!

---

## Управление шторками

**Файл:** `bookcabinet/hardware/shutters.py`

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

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| `bookcabinet/config.py` | GPIO_PINS (источник истины) |
| `tools/tray_platform.py` | Управление платформой |
| `tools/corexy_motion_v2.py` | Движение XY |
| `tools/startup_sequence.py` | Хоминг + калибровка |
| `tools/homing_pigpio.py` | Обертка хоминга |
| `bookcabinet/hardware/shutters.py` | Управление шторками |
| `bookcabinet/hardware/gpio_manager.py` | Абстракция GPIO |
| `calibration.json` | Координаты стоек/полок |
