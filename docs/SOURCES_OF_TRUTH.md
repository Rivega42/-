# Sources of Truth

Для каждой подсистемы BookCabinet указан единственный авторитетный источник.
При противоречиях с другими docs — этот файл побеждает.

Документ синхронизирован с текущим состоянием репозитория на 2026-04-17.
Если при работе встретили противоречие — доверяйте коду, указанному как **Primary**,
и сразу же исправляйте устаревший документ.

---

## GPIO пины

- **Primary:** `bookcabinet/config.py` (словарь `GPIO_PINS`)
- **Secondary:** `CLAUDE.md` раздел 5 (для Claude / agent context)
- **Deprecated:** Старые упоминания в `docs/HARDWARE.md` до 2026-04

Все скрипты в `tools/*.py` дублируют константы пинов — это сделано
сознательно для автономности диагностических утилит, но значения
ОБЯЗАНЫ совпадать с `GPIO_PINS`. Дубликаты помечены комментарием
`# IMPORTANT: These GPIO pin constants MUST match bookcabinet/config.py GPIO_PINS.`

## Механика / XY / Homing

- **Primary:** `tools/corexy_motion_v2.py` (каноническая реализация)
- **Operator entrypoint:** `tools/homing_pigpio.py`
- **Secondary:** `CLAUDE.md` разделы 7-8
- **App-level wrapper:** `bookcabinet/hardware/motors.py` (не первоисточник)

**HOME = LEFT + BOTTOM** — подтверждено живой cabinet session 2026-04-10.
Базовые безопасные скорости homing: `FAST=800`, `SLOW=300`,
`backoff_x=300`, `backoff_y=500` (см. `HOMING_SPEEDS` в `config.py`).

Старые упоминания `RIGHT+BOTTOM` и `FAST=1500` считаются историческими —
игнорируйте, не восстанавливайте.

## Tray Platform

- **Primary:** `tools/tray_platform.py`
- **Параметры:** `TRAY_FREQ = 12000 Hz`, travel ~21000 шагов, center ~10500 шагов
- **Критичные пины:** `TRAY_ENA_1=25`, `TRAY_ENA_2=26` должны быть LOW перед движением
- **Endstops:** `SENSOR_TRAY_END=7` (передний), `SENSOR_TRAY_BEGIN=20` (задний, с glitch filter 300μs)

## Замки (servo locks)

- **Primary:** `tools/book_sequences.py` (текущие PWM значения)
- **PWM:** `500μs` = open (язычок опущен, полка свободна),
  `1500μs` = close (язычок поднят, полка заперта),
  `0` = снятие нагрузки с сервопривода
- **Startup:** `tools/startup_calibration.py` устанавливает оба замка в
  нейтральную позицию (500μs), затем снимает PWM

Историческое упоминание "duty 2.5 / 7.5" в `config.py` относится к
старой модели через `RPi.GPIO` PWM и остаётся для справки.
Актуальный путь — pigpio `set_servo_pulsewidth()`.

## Шторки (relay outputs)

- **Primary:** `bookcabinet/hardware/shutters.py`
- **Пины:** `SHUTTER_OUTER=2` (SDA1), `SHUTTER_INNER=3` (SCL1)
- **Логика:** `HIGH=open`, `LOW=closed`
- **Startup:** оба пина инициализируются как OUTPUT, LOW (закрыто)

`docs/HARDWARE.md` может упоминать "shutters not found" — это устарело.

## RFID readers

| Ридер | Назначение | Primary источник |
|-------|-----------|------------------|
| ACR1281U-C (NFC 13.56 MHz) | ЕКП / библиотечный билет | `bookcabinet/rfid/card_reader.py` |
| IQRFID-5102 (UHF 900 MHz) | UHF карты / метки, Serial, протокол `0xA0` | `bookcabinet/hardware/iqrfid5102_driver.py` |
| RRU9816 (UHF 900 MHz) | UHF книжные метки, ~20 см | `bookcabinet/hardware/rru9816_driver.py` |
| Unified | Объединяющий слой для карт | `bookcabinet/rfid/unified_card_reader.py` |

- **Протокол IQRFID-5102:** начало кадра `0xA0`, checksum `(~SUM + 1) & 0xFF`
- **Серийные порты:** см. `RFID` dict в `bookcabinet/config.py`
- **Статус RRU9816:** работает на sidecar в `rru9816-sidecar/` (см. там README)

## ИРБИС

- **Primary client:** `bookcabinet/irbis/client.py`
- **Service layer:** `bookcabinet/irbis/service.py`
- **Mock:** `bookcabinet/irbis/mock.py` (используется, когда `IRBIS_MOCK=true`)
- **Параметры:** TCP порт `6666`, кодировка `cp1251`, команды A/B/C/D/K/G
- **Credentials:** только через env (`IRBIS_USERNAME`, `IRBIS_PASSWORD`) — без вшитых дефолтов

## API контракт (REST)

- **Primary:** `server/routes.ts` (TypeScript Express — основной backend для UI)
- **Документация:** `docs/API.md`
- **Python aiohttp routes** (`bookcabinet/server/api_routes.py`) — вторичны,
  для внутренних скриптов и legacy интеграций

Base URL: `http://<host>:5000`. WebSocket: `ws://<host>:5000/ws`.

## Python bridge

- **Primary:** `bookcabinet/bridge.py` — мост между TS сервером и Python hardware
- **Используется через:** env `PYTHON_BRIDGE_PATH` в `bookcabinet-ui.service`

## Калибровка

- **Runtime values:** `calibration.json` в корне репозитория
- **Schema + resolver:** `tools/calibration.py` (функция `resolve_cell()`)
- **Wizard / teach mode:** `tools/calib_4endstops.py`, `tools/calib_racks.py`, `tools/calibrate_xy.py`
- **Startup:** `tools/startup_calibration.py` запускается через
  systemd `bookcabinet-calibration.service` перед UI и daemon

Текущая версия калибровки указывается в поле `version` внутри `calibration.json`
(сейчас `2026-04-11-final`).

## Systemd сервисы

- **Unit-файлы:** `deploy/bookcabinet-*.service`
- **Install:** `deploy/install.sh`
- **Порядок запуска:** `pigpiod` → `bookcabinet-calibration` →
  `bookcabinet-daemon` → `bookcabinet-ui` → `chromium-kiosk`

Важно: в старых доках упоминается один сервис `bookcabinet` —
сейчас их несколько. Для ре-старта UI используйте `bookcabinet-ui`.

## База данных

- **Primary:** SQLite файл по пути из env `DATABASE_PATH`
  (по умолчанию `/home/admin42/bookcabinet/bookcabinet/data/shelf_data.db`)
- **Миграции:** Alembic, `alembic.ini` + `bookcabinet/migrations/`
- **Drizzle ORM (TS):** `drizzle.config.ts` — для TS-стороны

## Мониторинг / watchdog

- **Primary:** `bookcabinet/monitoring/watchdog.py`
- **Sentry init:** `bookcabinet/monitoring/sentry_init.py`
- **systemd WatchdogSec:** настроен в `bookcabinet-ui.service` (60 сек)

## Deprecated документы (игнорировать противоречия)

- `docs/ESP32_ARCHITECTURE.md` — ESP32 не используется, архитектура на RPi
- Устаревшие упоминания `RIGHT+BOTTOM` home corner во всех старых docs
- Упоминания `PUD_UP` для XY endstops в `docs/HARDWARE.md`
  (текущие XY motion скрипты используют `PUD_OFF` + `pressed=1`)
- `shelf-server.service` (старое имя) — реально сервисы называются `bookcabinet-*`
- Упоминания Arduino / Serial bridge — отклонены, см. `docs/DECISIONS.md`

---

## Как обновлять этот файл

1. При расхождении кода и этого документа — побеждает **Primary** источник
   (код). Документ обновляется до состояния кода.
2. При переезде подсистемы в новый файл — указывайте старый путь в
   Deprecated-секции с датой.
3. Не смешивайте "как должно быть" и "как есть" — этот файл фиксирует
   текущую реальность репозитория.
