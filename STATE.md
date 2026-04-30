# Состояние проекта BookCabinet

**Дата обновления:** 2026-04-30
**Версия:** в активной разработке (последний релиз — pending)
**Стадия:** Active development → подготовка к production deploy в Зеленогорской библиотеке

---

## В работе сейчас

- **Repo setup пакет** (ветка `chore/repo-setup`) — ✅ завершён локально (10 коммитов), ожидает review + merge. Vika issues заготовлены в `/tmp/vika_issues.md`.
- **Production issue/return workflow** (последний крупный merge — #79, #80) — проверка RFID, параллельные шторки, error recovery.
- **Калибровка** — per-rack калибровка обновлена, `tools/calibrate.py` стабилизирован.
- **`tools/move_shelf.py`** — auto-detect глубины ячейки по адресу.

## Заблокировано

- **gitleaks scan на истории** — нет binary в окружении агента, делегировано в issue для Vika.
- **GitHub admin действия** (Project v2, Environments, branch protection, Pages, Security Features) — собраны как `[devops:vika]` issues.
- **LICENSE подтверждение** — закладываем MIT, нужно подтверждение founders.

## Известные проблемы

- **`docs/HARDWARE.md` устарел** про шторки — CLAUDE.md §11.1 фиксирует пины 2/3, но HARDWARE.md ещё говорит "не найдены".
- **`tools/corexy_pigpio.py` хранит RIGHT+BOTTOM** как историческую правду (CLAUDE.md §8 — canonical now LEFT+BOTTOM).
- **`client/src/pages/kiosk.tsx` = 2372 строки** — кандидат на декомпозицию (P2/P3, не блокер).
- **Frontend без тестов** — vitest подключён, но тестов на TS/TSX нет.
- **RRU9816 status** — в QUICKSTART.md и PROJECT_INSTRUCTIONS.md разная правда. Не разрешено.

## Следующие шаги (по роадмапу)

См. `ROADMAP.md`. Краткое:

1. **Q2 2026 (текущий):** довести production deploy в Зеленогорской библиотеке. Стабилизировать issue/return flows на реальном железе. Снять диагностику с шкафа.
2. **Q3 2026:** масштабирование — второй шкаф, унификация калибровки, Telegram уведомления операторам.
3. **Q4 2026+:** ИРБИС глубокая интеграция, расширенная инвентаризация, дашборд для библиотекаря.

## Истоник правды для состояния

- **GitHub Issues** + лейблы `статус: *`
- **GitHub Project v2** (после ШАГА 8.1)
- **Этот файл** — high-level snapshot, обновляется по итогам каждого крупного коммита/PR.

## Связанные документы

- `ROADMAP.md`, `BACKLOG.md`, `DECISIONS.md`
- `CLAUDE.md` (project brief, hardware truth)
- `docs/SOURCES_OF_TRUTH.md`, `docs/DEVLOG.md`
