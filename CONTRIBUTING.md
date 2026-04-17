# Contributing

## Требования

- Node.js 20+ и npm
- Python 3.11+
- Raspberry Pi OS Bookworm/Trixie (для работы с реальным железом)
- pigpio (на RPi)

## Локальная разработка (без железа)

```bash
git clone https://github.com/Rivega42/-.git bookcabinet
cd bookcabinet
npm install
pip install -e .  # или uv sync
cp .env.example .env
# Поправить .env под себя. Для mock-режима:
# MOCK_MODE=true
npm run dev
```

UI: http://localhost:5000

## Установка на RPi

```bash
cd ~
git clone https://github.com/Rivega42/-.git bookcabinet
cd bookcabinet
sudo bash deploy/install.sh
sudo reboot
```

После ребута Chromium откроется в kiosk-mode на весь экран.

## Тесты

Frontend (Vitest):
```bash
npm test
```

Python (pytest):
```bash
pytest bookcabinet/tests/
```

Тесты разделены:
- **Mock-режим** — можно запускать локально
- **RPi-only** — требуют живое железо (motion, sensors, RFID)

## Workflow

1. **Ветки:** `feat/*`, `fix/*`, `docs/*`, `refactor/*`
2. **Commits:** [Conventional Commits](https://www.conventionalcommits.org/ru/):
   - `feat:` новая фича
   - `fix:` исправление бага
   - `docs:` документация
   - `refactor:` рефакторинг без изменения поведения
   - `perf:` оптимизация
   - `test:` тесты
3. **PR:** в main, с ссылкой на issue (`Closes #N`)
4. **Code review:** минимум 1 ревьюер для critical path (hardware, auth)

## Стиль кода

### TypeScript/React
- ESLint default config
- Prefer functional components with hooks
- Tailwind для стилей
- `as any` запрещён — используйте правильные типы

### Python
- Ruff + Black style (88 chars)
- `black bookcabinet/ tools/` перед commit
- Type hints на публичных API
- `print()` запрещён в production коде — только `logging`

### Коммит сообщения
- На английском, описание на русском допустимо
- Кратко и по делу

## Что требует RPi для тестирования

- ✋ Все механические последовательности (`tools/book_sequences.py`)
- ✋ Hardware sensors (`sensors.read_all()`)
- ✋ Реальные RFID ридеры (`unified_card_reader`)
- ✋ pigpiod daemon

Эти компоненты НЕ тестируются на CI, только вручную на шкафу.

## Mock mode

Для разработки без железа:
```bash
MOCK_MODE=true npm run dev
MOCK_MODE=true python3 bookcabinet/main.py
```

Mock подменяет:
- GPIO операции → no-op + log
- RFID ридеры → симуляция через `simulate_card()`
- Motion → asyncio.sleep вместо реального движения

## Документация

Если изменения затрагивают **hardware assumptions** — обновить:
1. `CLAUDE.md` (project brief для AI)
2. `docs/HARDWARE.md`
3. `docs/SOURCES_OF_TRUTH.md`

Если API изменился — обновить `docs/API.md` и `CHANGELOG.md`.

## Безопасность

- **Не коммитить секреты.** Используй env vars и `.env` (в .gitignore).
- **Не использовать** hardcoded пути вроде `/home/admin42/` — только через `BOOKCABINET_ROOT`.
- **Auth middleware** обязателен на любой endpoint меняющий состояние шкафа.
- Перед релизом запустить `gitleaks detect` или аналог.

## Issues и бэклог

- [GitHub Issues](https://github.com/Rivega42/-/issues)
- Приоритеты: `critical` → `bug`/`security` → `enhancement` → `docs`

## Контакты

- Maintainer: @Rivega42
- Telegram alerts: настраивается в `Settings Panel`
