# Changelog

Все значимые изменения проекта BookCabinet.
Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версионирование семантическое.

## [Unreleased]

### Added
- CI pipeline с typecheck + Python py_compile (.github/workflows/ci.yml)
- Systemd сервисы: `bookcabinet-daemon`, `bookcabinet-ui`, `bookcabinet-calibration`, `chromium-kiosk`
- `deploy/install.sh` — автоматическая установка на RPi
- Startup calibration: замки в нейтраль → XY homing → tray calibration
- Watchdog: disk space, CPU temperature, pigpiod liveness
- Alembic миграции БД (`bookcabinet/migrations/`)
- Optional Sentry error tracking (Python + Node)
- Health check эндпоинт `GET /api/health`
- Rate limiting на `/api/auth/card`, `/api/issue`, `/api/return`
- Session timeout (60с) с авто-logout и закрытием шторок
- Operation queue для последовательной обработки
- IRBIS offline sync queue с периодическим retry
- Journal log rotation (10MB × 5 backups)
- React Error Boundary на уровне App
- Lazy loading экранов (TeachMode, SettingsPanel, CabinetViewer, IssueProcess)
- `vite.config.ts` manualChunks для оптимизации bundle
- Высококонтрастная ЧБ-тема для outdoor kiosk
- Cal.com дизайн-система (переменные, touch 48px, transitions 150ms)
- Ч/Б тема в CabinetViewer
- Teach Mode + Settings на React (удалён Python static UI)
- Unit tests для critical path (Python + frontend)
- .env.example, README, CHANGELOG, CONTRIBUTING
- docs/SOURCES_OF_TRUTH.md, docs/DISASTER_RECOVERY.md, docs/API.md
- ARIA labels, keyboard navigation, touch targets 44px+

### Changed
- Auth: только по карте (убран PIN 1234)
- CoreXY скорости: возвращены к safe baseline (FAST=800, SLOW=300) после слipping теста 2026-04-10
- HOME corner: LEFT+BOTTOM (подтверждено на живом шкафу)
- Замки: PWM 500μs/1500μs с 0μs после установки (снятие нагрузки с сервы)
- Бизнес-логика выдачи/возврата: делегирована в Python через `bridge.py`
- IRBIS: вызывается ПОСЛЕ механики (не до)
- UID нормализация через `UnifiedCardReader`
- `motors.py` — тонкий адаптер над `corexy_motion_v2.py`
- Единое хранилище: JSON persistence для TS + SQLite WAL для Python
- Express/Node.js как единственный HTTP-сервер на :5000

### Fixed
- SQL injection в `db.py.update_cell/update_book` — whitelist колонок
- Hardcoded `/home/admin42/` paths → `BOOKCABINET_ROOT` env var
- Error handler `throw err` после `res.json()` — сервер падал
- API paths `/api/test/motors` → `/api/test/motor` (был 404)
- Endstop защита `DIR_TO_SENSOR` — нельзя двигаться к нажатому концевику
- Concurrent movement lock (`movementInProgress` + `asyncio.Lock`)
- Emergency stop разблокирует оба замка (книга не застревает)
- Tray endstops: glitch filter 300μs
- WebSocket memory leaks (reconnect timeout, stale closures)
- Duplicate auth race (WebSocket + mutation)
- `as any` в калибровочных мутациях — 13 мест
- Секреты в коде (MASTERKEY, WiFi пароль) убраны

### Security
- Auth middleware `requireSession` + `requireRole` на критичных эндпоинтах
- Zod валидация RFID (hex 8-48 chars) и card UID (6-48 chars)

## [0.3.0] — 2026-04 (Zelenogorsk cabinet session)

- Live cabinet testing подтвердил HOME = LEFT+BOTTOM
- Calibration.json с реальными замерами всех 21 полок
- Piecewise linear interpolation в `tools/calibration.py`
- `corexy_motion_v2.py` — canonical motion layer
- `tray_platform.py` — управление платформой (12000 Hz, ~21000 steps)
- `startup_sequence.py` — стартовая калибровка
- Systemd deployment

## [0.2.0] — 2026-03

- RFID readers: ACR1281 (NFC), IQRFID-5102 (UHF carts), RRU9816 (UHF books)
- `unified_card_reader.py` с параллельным опросом NFC + UHF
- Teach mode: запись/воспроизведение последовательностей
- Admin UI с калибровкой, тестированием механики
- IRBIS TCP client с search/read/write/format
- WebSocket handler для real-time событий
- Database models: cells, books, users, operations, system_logs, settings
- Shutters на pin 2/3, locks на pin 12/13 (PWM)

## [0.1.0] — 2026-01

- Initial prototype
- CoreXY motion через pigpio
- Basic GPIO mapping
- SQLite database init
- HTTP server (aiohttp)
