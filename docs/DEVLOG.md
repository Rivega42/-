# BookCabinet — Журнал разработки (DEVLOG)

> Этот файл содержит историю решённых проблем. Перед тем как "изобретать велосипед" — проверь, не решали ли мы это раньше.

**Теги для поиска:** `[rfid]` `[gpio]` `[rpi]` `[hardware]` `[software]` `[bugfix]` `[config]` `[docs]` `[sensors]`

---

## 📅 Январь 2026

### [2026-01-14] Калибровка датчиков TCST2103 — НАЙДЕНА ПРИЧИНА ШУМА! `[sensors]` `[gpio]` `[hardware]`

**Проблема:** Датчики TCST2103 сильно шумели (std=10-15), огоньки в мониторинге моргали.

**Что пробовали (не помогло):**
1. Увеличить SAMPLES (50 → 100)
2. Добавить debounce (200ms lockout)
3. Асимметричный debounce (быстрый ON, медленный OFF)
4. Внешние pull-up резисторы (200Ω — слишком мало, резистор слишком сильный)

**РЕШЕНИЕ:** Проблема была в **питании 5V вместо 3.3V!**

TCST2103 — датчик с открытым коллектором. Когда питали от 5V:
- Сигнал на GPIO был 5V
- GPIO Raspberry Pi рассчитан на **3.3V max**
- Отсюда шум, нестабильность, моргание

**Правильное подключение:**
```
Датчик     RPi
  +   →   3.3V  (НЕ 5V!)
  -   →   GND
  S   →   GPIO
```

**После перевода на 3.3V:**
- Y_BEGIN и Y_END — шум исчез, std < 3
- Стабильные показания без резисторов и конденсаторов

**Осталось:** Перенести X_BEGIN, X_END, TRAY_BEGIN, TRAY_END на 3.3V и перекалибровать.

**Скрипт калибровки:**
```bash
python3 tools/test_sensors.py --step   # пошаговая калибровка
python3 tools/test_sensors.py          # мониторинг (🔴/⚪)
```

**Калибровка сохраняется в:** `~/bookcabinet/sensor_calibration.json`

**Commit:** f47d5e160dd9f1163c616d6f7144e5f41e048753

---

### [2026-01-14] RFID система полностью настроена и протестирована `[rfid]` `[hardware]` `[bugfix]`

**Сессия завершена:** Все три RFID считывателя работают корректно.

**Исправлена проблема с NFC (ACR1281U-C):**
- **Проблема:** Считыватель пикал при поднесении карты, но UID не передавался
- **Причина:** ACR1281 имеет 3 интерфейса (00 00, 00 01, 00 02), карты читаются на интерфейсе 00 01 (contactless)
- **Решение:** Обновлён `unified_card_reader.py` для опроса всех трёх интерфейсов
- **Результат:** NFC карта `04239092F17380` успешно читается

**Исправлена проблема переподключения:**
- **Проблема:** После вызова disconnect() считыватели не подключались заново
- **Причина:** Метод disconnect() сбрасывал флаги _nfc_available и _uhf_available
- **Решение:** Добавлен метод _disconnect_readers() который отключает устройства без сброса флагов
- **Commit:** abe91614c79b1557696cd95026e494137fa5275c

**Попытка увеличить дальность IQRFID-5102:**
- **Проблема:** Дальность всего 3-5 см
- **Исследование:** Устройство UHF Reader Bee02 V1.6 с печатной антенной на плате
- **Попытки:** Добавлены методы set_power() и get_power() в драйвер
- **Результат:** Мощность не регулируется, команды возвращают ошибки (0xFF)
- **Вывод:** Аппаратное ограничение встроенной антенны

**КРИТИЧЕСКАЯ ПРОБЛЕМА — стекло 8мм:**
- **Требование:** Считыватели должны быть установлены за стеклом толщиной 8мм
- **Проблема:** При такой толщине стекла дальность упадёт критически:
  - NFC: с 5-10см до 0-3см
  - UHF: с 3-5см до 0см (не будет работать)
- **Варианты решения:**
  1. Вырезать окна в стекле
  2. Использовать выносные антенны
  3. Заменить считыватели на модели с внешними антеннами

**Итоговое тестирование:**
```bash
python3 test_rfid_readers.py
# NFC: 04239092F17380 (библиотечный билет)
# UHF: 304DB75F19600009F0022743 (ЕКП карта)
```

**Созданные утилиты:**
- `test_rfid_readers.py` — комплексный тест с цветным выводом и статистикой
- `configure_rfid_power.py` — попытка настройки мощности (не эффективна для IQRFID-5102)
- `test_nfc_all_interfaces.py` — проверка всех интерфейсов ACR1281

**Важные выводы:**
- UHF считыватели требуют USB хаб с внешним питанием
- IQRFID-5102 имеет фиксированную мощность
- Для работы через стекло нужны другие считыватели или выносные антенны

---

### [2026-01-13] Systemd + реальный режим работы `[config]` `[rpi]`

**Что сделано:**
1. Systemd сервис переведён на `MOCK_MODE=false`
2. Исправлен `unified_card_reader.get_status()` — возвращает правильные ключи для API

**Файлы:**
- `/etc/systemd/system/bookcabinet.service` — `Environment=MOCK_MODE=false`
- `bookcabinet/rfid/unified_card_reader.py` — добавлены ключи `nfc_connected`, `uhf_connected`, `polling`

**Баг обнаружен:** `irbisConnected` в диагностике показывает `not IRBIS['mock']` вместо реального статуса. RPi не в сети библиотеки → `nc -zv 172.29.67.70 6666` = "No route to host"

**Commit:** 7d7b2c4

---

### [2026-01-13] Тесты RFID на реальном оборудовании `[rfid]` `[hardware]`

**Оборудование:**
- IQRFID-5102 → /dev/ttyUSB0 (карты UHF) ✅ работает
- RRU9816 → /dev/ttyUSB1 (книжные метки) ✅ работает
- ACR1281U-C (NFC) — не подключён в этой сессии

**Результаты тестов:**
```bash
python3 bookcabinet/hardware/iqrfid5102_driver.py /dev/ttyUSB0
# ✅ Читательский билет: 304DB75F19600003F0085515

python3 bookcabinet/hardware/rru9816_driver.py /dev/ttyUSB1
# ✅ Книжная метка: 304DB75F1960000300102E96
```

**Сервер в реальном режиме:**
```bash
cd ~/bookcabinet/bookcabinet
MOCK_MODE=false python3 main.py
# NFC=False, UHF=True
# Карты читаются, события отправляются
```

**Проблема:** Оба считывателя используют CP2102 с одинаковым VID/PID — нельзя различить по udev, только по физическому порту USB.

---

### [2026-01-13] WiFi на RPi3 — чип повреждён `[rpi]` `[hardware]`

**Проблема:** wlan0 не появляется после перезагрузки

**Диагностика:**
```bash
vcgencmd get_throttled    # 0x50005 — under-voltage NOW
dmesg | grep mmc1         # "Failed to initialize a non-removable card"
ip link show wlan0        # Device does not exist
```

**Что пробовали:**
1. Заменили кабель питания — напряжение поднялось с 3.27V до 4.9V ✓
2. `vcgencmd get_throttled` → 0x0 после перезагрузки ✓
3. Но mmc1 (SDIO шина WiFi) всё равно Failed
4. `sudo dtoverlay sdio` — DMA выделился, но чип не отвечает
5. GPIO 41 (WL_ON) был в LOW — включили через `pinctrl set 41 op dh`
6. `sudo modprobe brcmfmac` — драйвер грузится, но чип не видит

**Вывод:** WiFi чип BCM43430 повреждён от длительной работы при под-напряжении (3.27V критично!)

**Решение:** Использовать USB WiFi адаптер (TP-Link TL-WN725N и т.п.) или работать через Ethernet

**Полезные команды для диагностики WiFi:**
```bash
vcgencmd get_throttled           # 0x0 = OK, 0x50005 = undervolt NOW
ls /sys/bus/sdio/devices/        # пусто = чип не виден
rfkill list all                  # WiFi должен быть в списке
pinctrl get 41                   # WL_ON: должен быть HIGH (dh)
dmesg | grep -i mmc1             # ошибки инициализации
```

---

### [2026-01-13] Реальные тесты RFID с таймаутом `[rfid]` `[software]`

**Что сделано:** Добавлены API endpoints для реального тестирования считывателей

**Новые endpoints:**
- `POST /api/test/rfid/read-card` — ждёт карту до 30 сек
  - `{timeout: 10, reader: "nfc"|"uhf"|"any"}`
  - Возвращает UID и источник
- `POST /api/test/rfid/read-book` — ждёт книжную метку
  - `{timeout: 10}`
  - Возвращает данные от RRU9816

**Логика:** Временно подменяет callback, ждёт Event или таймаут, восстанавливает callback.

**Commit:** 87e4e06

---

### [2026-01-13] Исправлено отображение RFID в диагностике `[rfid]` `[bugfix]`

**Проблема:** Админ-панель показывала boolean вместо строк для статуса считывателей

**Было:** `{nfc: true, uhf_card: true, book: true}`
**Стало:** `{'ACR1281U-C (карты NFC)': 'connected', ...}`

**Правильная маркировка считывателей:**
- ACR1281U-C (карты NFC) — ЕКП, 13.56MHz
- IQRFID-5102 (карты ЕКП) — читательские билеты UHF 900MHz, внешняя панель
- RRU9816 (книги) — UHF, внутри шкафа

**Commit:** 198be9b3

---

### [2026-01-13] IQRFID-5102 — драйвер готов! `[rfid]` `[hardware]`

**Протокол IQRFID-5102:**
```
Формат: [LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]
Baudrate: 57600
CRC-16: polynomial 0x8408, init 0xFFFF
```

**Команда Inventory:**
```
TX: 04 00 01 DB 4B
    │  │  │  └─ CRC-16
    │  │  └─ CMD = 0x01
    │  └─ ADR = 0x00
    └─ LEN = 4
```

**Ответ (метка найдена):**
```
RX: 13 00 01 01 01 0C [12 bytes EPC] [CRC]
    │  │  │  │  │  └─ EPC length
    │  │  │  │  └─ RSSI
    │  │  │  └─ Tag count
    │  │  └─ CMD
    │  └─ ADR
    └─ LEN
```

**Ответ (нет меток):**
```
RX: 05 00 01 FB F2 3D
              └─ Status 0xFB = no tags
```

**Результат:** Создан драйвер `bookcabinet/hardware/iqrfid5102_driver.py`

**Тестирование:**
```bash
# Windows
py bookcabinet/hardware/iqrfid5102_driver.py COM2

# RPi
python3 bookcabinet/hardware/iqrfid5102_driver.py /dev/ttyUSB0
```

---

### [2026-01-13] RRU9816 — реверс протокола, драйвер для RPi готов! `[rfid]` `[hardware]`

**Проблема:** RRU9816 требует Windows + закрытую DLL, нельзя использовать на RPi

**Решение:** Реверс-инжиниринг протокола через serial sniffer (com0com + Python)

**Что выяснили:**
- Протокол **НЕ** стандартный 0xA0
- Формат: `[длина] [адрес] [cmd] [данные] [CRC-16]`
- Baudrate: 57600
- Адрес: 0x00 (или 0xFF для broadcast)

**Ключевые команды:**
```
Get Info:   04 FF 21 19 95
Inventory:  09 00 01 01 00 00 80 0A 76 FC
```

**Формат ответа Inventory с меткой:**
```
[15] 00 01 01 01 01 0C [EPC 12 байт] [CRC-16]
     │     │  │  │  └─ длина EPC
     │     │  │  └─ кол-во меток  
     │     │  └─ статус (01=найдена, 00=нет)
     │     └─ команда
     └─ адрес
```

**Результат:** Создан драйвер `bookcabinet/hardware/rru9816_driver.py`
- Работает на Windows (проверено)
- Готов для RPi (/dev/ttyUSB0)
- Не требует DLL!

**Тестирование:**
```bash
# Windows
py bookcabinet/hardware/rru9816_driver.py COM2

# RPi
python3 bookcabinet/hardware/rru9816_driver.py /dev/ttyUSB0
```

**Инструменты реверса:**
- `tools/serial_sniffer.py` — MITM прокси для перехвата трафика
- `tools/test_rru9816_protocol.py` — тесты разных протоколов

---

### [2026-01-13] Создана система документации `[docs]` `[config]`

**Что сделано:**
- QUICKSTART.md — точка входа для Claude
- docs/TODO.md — текущие задачи
- docs/DEVLOG.md — история (этот файл)
- docs/DECISIONS.md — архитектурные решения
- docs/GLOSSARY.md — терминология (инверсии!)
- docs/HARDWARE.md — инвентарь оборудования
- docs/TROUBLESHOOTING.md — проблемы требующие физ. доступа

**Цель:** Claude помнит контекст между сессиями, не повторяет решённые проблемы.

---

### [2026-01-10] WiFi на RPi3 не работает `[rpi]` `[hardware]`

**Проблема:** `iwconfig` не показывает wlan0

**Диагностика:**
```bash
vcgencmd get_throttled  # Показало 0x50005 — under-voltage!
```

**Причина:** Слабый блок питания — WiFi чип не стартует при под-напряжении

**Решение:** Заменить БП на 5V/2.5-3A

---

### [2026-01-10] Тачскрин инвертирован по Y `[hardware]` `[config]`

**Проблема:** Касание вверху экрана регистрируется внизу

**Решение:** udev rule с матрицей трансформации:
```bash
sudo nano /etc/udev/rules.d/99-touchscreen.rules
```
```
ENV{ID_VENDOR_ID}=="222a", ENV{ID_MODEL_ID}=="0001", ENV{LIBINPUT_CALIBRATION_MATRIX}="1 0 0 0 -1 1 0 0 1"
```

---

### [2026-01-10] Датчики показывают инверсную логику `[gpio]` `[bugfix]`

**Проблема:** Ожидали raw=1 когда нажат, получали raw=0

**Причина:** Датчики с NPN выходом — при срабатывании притягивают к земле

**Решение:** Инвертировать логику в коде:
```python
pressed = (GPIO.input(pin) == GPIO.LOW)  # НЕ HIGH!
```

---

## 📅 Декабрь 2025

### [2025-12-23] Python сервер не запускается на Windows `[software]` `[bugfix]`

**Проблема:** BAT файл открывается и сразу закрывается

**Причина 1:** Путь содержит кириллицу — проблемы с кодировкой

**Причина 2:** Не установлен pyserial

**Решение:**
```cmd
pip install pyserial
cd C:\путь\к\проекту
python shelf_server.py COM8
```

---

## 📅 Сентябрь 2025

### [2025-09-14] Выбор технологии — Python + RPi `[docs]`

**Решение:** Используем Raspberry Pi напрямую для управления GPIO (без Arduino)

**Причины:**
- Один контроллер вместо двух
- Python для всего — сервер, GPIO, RFID
- Встроенные подтяжки GPIO
- См. docs/DECISIONS.md для деталей

---

## 🔗 Полезные ссылки

- Референс ИРБИС: https://github.com/valinerosgordov/RFIDShkafWithIRBIS
- ИРБИС API: TCP порт 6666, кодировка cp1251
- Терминология: docs/GLOSSARY.md
- Оборудование: docs/HARDWARE.md

## 📅 Апрель 2026

### [2026-04-10] CoreXY v2 стал каноническим слоем движения `[motion]` `[homing]` `[pigpio]`

**Что сделали:**
- перевели `tools/corexy_motion_v2.py` в import-safe reusable layer
- зафиксировали safe baseline: `HOME=LEFT+BOTTOM`, `FAST=800`, `SLOW=300`, `BACKOFF_X=300`, `BACKOFF_Y=500`
- перевели `tools/homing_pigpio.py` на thin wrapper поверх v2

**Live-проверка:**
- read-only state показал `LEFT=1`, `BOTTOM=1`
- новый `python3 tools/homing_pigpio.py` успешно прошёл полный homing
- `python3 tools/corexy_motion_v2.py y-sweep` успешно дошёл до `TOP` и вернулся в `BOTTOM`

**Вывод:**
- v2-примитивы теперь подтверждены на реальном шкафе не только для `x-sweep`, но и для `homing` и `y-sweep`
- следующий логичный шаг: убрать дублирование / расхождения в `bookcabinet/hardware/motors.py` и посадить app-level слой на ту же каноническую truth
