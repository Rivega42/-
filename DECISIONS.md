# Архитектурные решения (DECISIONS) — корневой лог

> Здесь — высокоуровневые решения по проекту BookCabinet.
> Конкретные hardware-решения и более ранние записи — в `docs/DECISIONS.md`.
> Новые записи добавляются в начало.

---

## ADR-008 — `chore/repo-setup` пакет (этот PR)
- **Дата:** 2026-04-30
- **Контекст:** репо разрослось, нужна единая структура (issue/PR templates, CI/CD, automation, AI-правила, дашборд).
- **Решение:** применить `repo-setup-kit` шаблон (10 шагов) на ветке `chore/repo-setup`. Существующее не переписывать, только дополнять.
- **Последствия:** появляются `STATE.md`, `ROADMAP.md`, `BACKLOG.md`, `LICENSE`, `SECURITY.md`, `docs/ai/`, `docs/context/`, workflow-ы автоматизации, скаффолд дашборда.
- **Альтернативы:** оставить как есть — отклонено, проект готовится к production deploy и нужна дисциплина.

## ADR-007 — HOME corner = LEFT+BOTTOM
- **Дата:** 2026-04-10 (live cabinet session)
- **Контекст:** конфликт между ранней документацией (RIGHT+BOTTOM) и реальным поведением шкафа.
- **Решение:** canonical HOME = `LEFT+BOTTOM`. `bookcabinet/config.py` использует `LEFT_BOTTOM`. `tools/corexy_motion_v2.py` — canonical motion layer. `tools/homing_pigpio.py` — стабильный CLI wrapper.
- **Последствия:** старые упоминания `RIGHT_BOTTOM` в `tools/corexy_pigpio.py` и старых docs остаются как историческая запись расследования.
- **Источник правды:** CLAUDE.md §8.

## ADR-006 — homing baseline 800/300 (после belt slip)
- **Дата:** 2026-04-10
- **Контекст:** скорости 1500/400 в `tools/corexy_pigpio.py` вызвали belt slip в живой сессии.
- **Решение:** для homing использовать FAST=800, SLOW=300. Не повышать без проверки на железе.
- **Последствия:** `tools/homing_pigpio.py` — единственный canonical homing tool на этих скоростях.

## ADR-005 — шторки на пинах 2/3
- **Дата:** 2026 (зафиксировано в CLAUDE.md §11.1)
- **Решение:** `SHUTTER_OUTER = 2`, `SHUTTER_INNER = 3`, LOW=closed, HIGH=open.
- **Последствия:** `docs/HARDWARE.md` устарел в этой части и должен быть обновлён.

## ADR-004 — PWM замки на servo (LOCK_FRONT=12, LOCK_REAR=13)
- **Дата:** 2025-12 / 2026-01
- **Решение:** 50 Hz, duty 2.5 = open (полка свободна), 7.5 = close (заперто).
- **Контр-интуиция:** "open" = язычок опущен, "close" = язычок поднят (см. CLAUDE.md §5.5).

## ADR-003 — Python 3.11 + Node.js 20 (гибридный стек)
- **Дата:** 2025-09 (Python), 2025-Q4 (Node)
- **Решение:** Python для hardware control + бизнес-логики; Node/Express + React для kiosk UI и API.
- **Причины:** Python нативен для GPIO/pigpio/RFID; React/Vite даёт modern kiosk UI, обновляемый без пересборки Python; разделение слоёв через локальный bridge.
- **Альтернативы:** монолит на Python + Flask + Jinja — отклонено как устаревший UX.

## ADR-002 — ЧБ-тема + крупный touch (44px+)
- **Дата:** 2026-Q1
- **Решение:** kiosk UI — высококонтрастный ч/б дизайн, минимум 44px touch targets, ARIA.
- **Причины:** kiosk на public space, разные lighting conditions, accessibility.
- **Источник правды:** `docs/ai/CLAUDE_DESIGN_RULES.md` (создаётся в ШАГЕ 4).

## ADR-001 — Один контроллер (RPi), без Arduino
- **Дата:** 2025-12
- **Решение:** RPi управляет всем — GPIO, сервер, UI.
- **Подробности:** см. `docs/DECISIONS.md`.

---

*Более старые архитектурные/hardware решения — в `docs/DECISIONS.md`.*
