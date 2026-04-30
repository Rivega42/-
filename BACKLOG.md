# Бэклог BookCabinet

> **Источник правды:** GitHub Issues с лейблом `статус: бэклог`.
> **Дашборд:** будет доступен по URL после ШАГА 9.
> **Этот файл** — высокоуровневая навигация по бэклогу. Не дублируем содержимое issues здесь.

---

## Где искать задачи

| Тип | Где |
|---|---|
| Активные issues | https://github.com/Rivega42/-/issues |
| Эпики (EPIC лейбл) | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3Aepic |
| Бэклог | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3A"статус%3A+бэклог" |
| В работе | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3A"статус%3A+в+работе" |
| Заблокировано | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3A"статус%3A+блокер" |
| DevOps для Vika | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3Avika |
| Нужна инфа founders | https://github.com/Rivega42/-/issues?q=is%3Aissue+label%3A"статус%3A+нужна+инфа" |

---

## Сейчас в спринте (Q2 2026 — Production Deploy)

См. milestone "Production Deploy" в GitHub.

Ключевые направления:
- Стабилизация issue/return на реальном железе
- ИРБИС integration smoke-test в библиотеке
- Telegram уведомления оператору
- Финал repo setup (этот PR)

## Up Next (после Production Deploy)

См. ROADMAP.md → Q3 2026:
- Mechanical reliability
- Декомпозиция `kiosk.tsx`
- Frontend tests
- Второй шкаф
- Operator dashboard

## Discovery

Идеи и темы для исследования (заводятся как issues с лейблом `тип: discovery`):
- Predictive maintenance на основе моторных логов
- Mobile UX для читателя (приложение vs web)
- Multi-tenant для сети шкафов

## Idea Pool

Сырые идеи без обязательств — issues с лейблом `тип: идея`:
- Open-source release
- Библиотечный API стандарт
- Интеграция с городскими картами

## Заблокировано

Issues с лейблом `статус: блокер`. Следить отдельно.

---

## Глобальные ограничения / запретные зоны

- `bookcabinet/config.py` — GPIO map. Изменения только с подтверждением Roman после live cabinet session.
- `tools/corexy_motion_v2.py`, `tools/homing_pigpio.py` — canonical motion. Не «оптимизировать» без подтверждения.
- `tools/calib_*.py`, `patch_*.py`, `x_*_debug*.py` — field knowledge, не удалять.

См. также `CLAUDE.md` §3 (mission-critical rule set).
