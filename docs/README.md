# Карта документации BookCabinet

> Это индекс всей документации репозитория. Если файла нет здесь — он либо в архиве, либо устарел.

---

## Корень репо (high-level)

| Файл | Назначение |
|---|---|
| [`../README.md`](../README.md) | Точка входа |
| [`../CLAUDE.md`](../CLAUDE.md) | Project brief для AI, hardware truth, safety rules |
| [`../STATE.md`](../STATE.md) | Текущее состояние, что в работе, известные проблемы |
| [`../ROADMAP.md`](../ROADMAP.md) | Квартальный план |
| [`../BACKLOG.md`](../BACKLOG.md) | Навигация по GitHub Issues |
| [`../DECISIONS.md`](../DECISIONS.md) | Архитектурные решения (root level) |
| [`../CHANGELOG.md`](../CHANGELOG.md) | История изменений |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Как контрибьютить |
| [`../SECURITY.md`](../SECURITY.md) | Security policy |
| [`../LICENSE`](../LICENSE) | MIT License |
| [`../QUICKSTART.md`](../QUICKSTART.md) | Быстрый старт |
| [`../PROJECT_INSTRUCTIONS.md`](../PROJECT_INSTRUCTIONS.md) | Инструкции по проекту |
| [`../AUDIT.md`](../AUDIT.md) | Аудит репо (2026-04-30) |

---

## `docs/` — детальная документация

### Hardware / Architecture
- [`HARDWARE.md`](HARDWARE.md) — GPIO map, моторы, сенсоры, замки. ⚠ Раздел про шторки устарел, см. CLAUDE.md §11.1.
- [`ESP32_ARCHITECTURE.md`](ESP32_ARCHITECTURE.md) — Архитектура с ESP32 (если используется).
- [`SOURCES_OF_TRUTH.md`](SOURCES_OF_TRUTH.md) — где какая правда живёт.

### API / Integration
- [`API.md`](API.md) — REST API спецификация.
- [`FRONTEND_BACKEND_INTEGRATION.md`](FRONTEND_BACKEND_INTEGRATION.md) — связка React ↔ Express ↔ Python.
- [`IRBIS_INTEGRATION.md`](IRBIS_INTEGRATION.md) — ИРБИС TCP/cp1251 интеграция.
- [`RFID_READERS.md`](RFID_READERS.md) — ACR1281U-C, IQRFID-5102, RRU9816.
- [`RFID_SETUP_REPORT.md`](RFID_SETUP_REPORT.md) — отчёт по настройке.

### Operations
- [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md) — recovery procedures (runbook).
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — known issues и фиксы.
- [`DEVLOG.md`](DEVLOG.md) — дневник разработки.
- [`SESSION_2026-04-16.md`](SESSION_2026-04-16.md) — лог сессии.

### Process / History
- [`DECISIONS.md`](DECISIONS.md) — hardware/business решения с причинами.
- [`TODO.md`](TODO.md) — старый TODO (мигрируется в GitHub Issues).
- [`GLOSSARY.md`](GLOSSARY.md) — алфавитный глоссарий.

---

## Подпапки `docs/`

- [`adr/`](adr/) — Architecture Decision Records (новый формат, см. `adr/README.md`).
- [`architecture/`](architecture/) — диаграммы, описания подсистем.
- [`api/`](api/) — детальные API references (по мере роста).
- [`runbooks/`](runbooks/) — пошаговые операционные инструкции.
- [`guides/`](guides/) — howto / tutorials для контрибьюторов.
- [`ai/`](ai/) — правила для AI-исполнителей (Claude Code, Vika).
- [`prompts/`](prompts/) — системные промпты как код.
- [`context/`](context/) — бизнес-контекст для AI (PRODUCT, DOMAIN).

---

## Связи

- Корневой `DECISIONS.md` — высокоуровневые ADR (новые).
- `docs/DECISIONS.md` — старые hardware/business решения.
- `docs/adr/` — формальные ADR в виде отдельных файлов.

При расхождении — приоритет CLAUDE.md (hardware truth) > root DECISIONS.md > docs/DECISIONS.md > старые docs.
