# Правила для Claude Code (этот агент)

> Это правила для меня (Claude Code) при работе в репо BookCabinet.

---

## Перед началом любой сессии

1. Прочитать `STATE.md` — что в работе сейчас.
2. Прочитать `CLAUDE.md` — hardware truth, safety rules.
3. При работе над эпиком — найти его GitHub issue и под-issues.
4. Если в `STATE.md` записано "blocked by X" — сначала разрулить X или выбрать другую задачу.

## Коммиты

- **Conventional Commits обязательно:** `<type>(<scope>): <subject>`
- Типы: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `build`.
- Scope: `(audit)`, `(docs)`, `(ci)`, `(structure)`, `(automation)`, `(github)`, `(dashboard)`, `(hardware)`, `(rfid)`, `(irbis)`, `(kiosk)`, `(motion)`.
- Subject — повелительное наклонение, без точки в конце, ≤72 символов.
- В body — что и почему. В footer — `Closes #N`, `Refs #N`.
- Один коммит = одна логическая единица.

## Branch naming

- `feat/<short-name>` — новая фича.
- `fix/<short-name>` — багфикс.
- `chore/<short-name>` — поддержка, репо.
- `docs/<short-name>` — только документация.
- `refactor/<short-name>` — рефакторинг без изменения поведения.
- `claude/<topic>` — экспериментальные ветки от Claude Code.
- НИКОГДА не пушить напрямую в `main` или `master`.

## Pull Requests

- Шаблон в `.github/PULL_REQUEST_TEMPLATE.md` обязательно заполнен.
- Привязать к issue: `Closes #N`.
- Указать тип изменения и риски (особенно для motion / GPIO).
- Если меняется hardware-related код — отметить в описании "Требует валидации на железе" и не мержить без подтверждения Roman.

## Запретные зоны (не трогать без явного разрешения)

См. `CLAUDE.md` §3 (mission-critical rule set). Кратко:

- `bookcabinet/config.py` (GPIO map) — менять только после live cabinet session.
- `tools/corexy_motion_v2.py`, `tools/homing_pigpio.py` — canonical motion.
- `tools/calib_*.py`, `patch_*.py`, `x_*_debug*.py` — field knowledge.
- Direction safety map в motion scripts — не убирать.

## State updates после работы

После значимого PR / коммита:
- Обновить `STATE.md` (разделы "В работе сейчас", "Известные проблемы").
- При архитектурном решении — добавить запись в `DECISIONS.md`.
- При обнаружении расхождения между docs и кодом — отметить в `AUDIT.md` или открыть issue с лейблом `tech-debt`.

## Когда **не** делать сам

Делегировать в issue для Vika (`[devops:vika]`):
- GitHub admin: branch protection, environments, secrets, Pages, security features.
- Org-level настройки.
- Ротация секретов.
- Применение лейблов через `gh label create` (если `gh` нет в окружении).

Делегировать founders (issue с лейблом `статус: нужна инфа`):
- Юридические вопросы (лицензия, ToS).
- Бизнес-приоритеты.
- Ключи к prod-окружениям.

## Тесты

- Python: `vitest`-аналог = `pytest`. Тесты в `bookcabinet/tests/`.
- Node/TS: `vitest run` (см. `package.json`).
- Любая новая business-логика должна иметь хотя бы smoke-test.
- Hardware-related коду — mock-mode тесты обязательны (см. `bookcabinet/hardware/motors.py` mock fallback).

## Стиль кода

- Python — следовать существующему стилю репо (PEP8, 4 пробела). Не вводить black/ruff в этом PR.
- TS/TSX — существующий стиль (Prettier-friendly, 2 пробела). Не trigger глобального reformat.
- Markdown — соблюдать `.editorconfig`.

## Работа с секретами

- Никогда не читать и не выводить значения `.env`.
- Никогда не коммитить файлы `.env`, `*.key`, `*.pem`.
- При обнаружении секрета в коде — НЕМЕДЛЕННО создать P0 issue для Vika.

## Ограничения от среды агента

- Не пушить в remote без явного разрешения пользователя.
- Не создавать GitHub issues через `gh` без подтверждения — собирать в `/tmp/vika_issues.md`.
- Не запускать диагностические скрипты, которые могут двинуть моторы (см. `tools/corexy_*.py`).

## Общение

- Технические термины — на английском.
- Артефакты документации — на русском.
- Не использовать emoji в коммитах и коде (только если явно просят).
