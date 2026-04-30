# Аудит репозитория BookCabinet

**Дата:** 2026-04-30
**Аудитор:** Claude Code
**Ветка:** `chore/repo-setup`

---

## Контекст

- **Репо:** `Rivega42/-` (BookCabinet)
- **Стек:** Python 3.11 (aiohttp, pigpio, RPi.GPIO) + Node.js 20 (Express, React 18, TypeScript, Vite, Tailwind, Drizzle)
- **Тип:** Embedded + Web kiosk + RFID/NFC + ИРБИС интеграция
- **Стадия:** Active development → подготовка к production deploy в Зеленогорской библиотеке (Q2 2026)
- **Размер:** 104 .py + 89 .ts/.tsx + 35 .md (без `node_modules`/`dist`)
- **Хост-целевая платформа:** Raspberry Pi 3 на физическом шкафу
- **Ветка работы:** `chore/repo-setup` (на основе `main`)

---

## Сильные стороны (сохранить и уважать)

- **Подробная документация** в `docs/` (15 файлов: API, HARDWARE, DEVLOG, DISASTER_RECOVERY, IRBIS_INTEGRATION, RFID_READERS, SOURCES_OF_TRUTH, TODO, TROUBLESHOOTING и др.)
- **Канонический project brief** `CLAUDE.md` с зафиксированной железной правдой (HOME=LEFT+BOTTOM, GPIO map, скорости 800/300, направления CoreXY).
- **Базовая документация** в корне: README, QUICKSTART, PROJECT_INSTRUCTIONS, CHANGELOG, CONTRIBUTING (созданы в #68).
- **Working CI** (`.github/workflows/ci.yml`) — typecheck (Node) + py_compile (Python). Прошёл стабилизацию: lock-file sync, pcscService filter.
- **Hardware протестирован** на реальном шкафу — homing, motion baseline 800/300 после belt slip 2026-04-10, конкретные real-world данные.
- **Активная работа** — 8+ PR смержено за последнюю неделю (см. `git log`).
- **Deploy infra** — systemd units в `deploy/` (daemon, ui, calibration, chromium-kiosk) + `install.sh`.
- **Issue tracking** — 80+ issues (открытых/закрытых) на GitHub.
- **Domain-specific tooling** в `tools/` — 30+ диагностических/калибровочных скриптов с реальной field-knowledge ценностью.
- **Существующие docs/DECISIONS.md и docs/GLOSSARY.md** — не дублировать, расширять.

## Существующие конвенции (уважать, не переписывать)

- **Conventional commits** уже используются (`feat:`, `fix:`, `chore:`, см. `git log`).
- **CLAUDE.md** — высший уровень project context. Не переписывать.
- **Двуязычная документация** — русский основной язык, английский для технических терминов.
- **Backup/debug файлы сохраняются** (см. CLAUDE.md §11.5: `patch_*.py`, `x_homing_debug*.py`).
- **Tools/ — это field-knowledge архив**, не «production cleanup».
- **GPIO map в `bookcabinet/config.py`** — единственный источник правды для пинов.
- **Стиль PR** — крупные смерженные PR с указанием `closes #N` (см. #68, #79, #80).
- **Issue templates** — пока нет. Issues создаются свободной формой.

---

## Что сломано / устаревшее

- **`docs/HARDWARE.md` содержит устаревшие сведения** про шторки (CLAUDE.md §11.1 — шторки на пинах 2/3 уже подтверждены, но HARDWARE.md ещё не обновлён).
- **HOME corner inconsistency** — старые упоминания `RIGHT_BOTTOM` в `tools/corexy_pigpio.py` (CLAUDE.md §8 фиксирует это как историю; canonical `LEFT_BOTTOM`).
- **Endstop polarity** — расхождения между HARDWARE.md (PUD_UP/HIGH-triggered) и `tools/corexy_motion_v2.py` (PUD_OFF, pressed=1).
- **RRU9816 status** — противоречие в QUICKSTART.md (работает) vs PROJECT_INSTRUCTIONS.md (требует Windows DLL, не используется).
- **`docs/TODO.md` и `docs/DEVLOG.md`** отстают от реальности — много новой работы есть только в коде.
- **Нет LICENSE файла** — README говорит MIT, но LICENSE не приложен.
- **Существующий `ci.yml` минимален** — нет lint, нет tests run, нет gitleaks, нет CodeQL.

## Что отсутствует

- `STATE.md` — текущее состояние.
- `ROADMAP.md` — квартальный план.
- `BACKLOG.md` — линк на GitHub Issues.
- `SECURITY.md` — security policy.
- `LICENSE` — файл лицензии.
- `.editorconfig`, `.gitattributes`.
- `docs/adr/`, `docs/architecture/`, `docs/runbooks/`, `docs/guides/`, `docs/ai/`, `docs/prompts/`, `docs/context/`.
- `docs/README.md` — карта документации.
- `.github/CODEOWNERS`.
- `.github/ISSUE_TEMPLATE/` (и `PULL_REQUEST_TEMPLATE.md`).
- `.github/dependabot.yml`.
- `.pre-commit-config.yaml`.
- Workflow-ы автоматизации (auto-labels, rollup, deps, validate, digest, notify, dashboard-sync, release-please, deploy-staging/prod).
- `scripts/` директория (нет даже setup-labels.sh).
- `infra/` директория.
- `tools/dashboard/`.
- `_archive/`.

## Технический долг

- **`client/src/pages/kiosk.tsx` = 2372 строки** — монолитный компонент, тяжело поддерживать. P2 кандидат на декомпозицию.
- **Нет фронтенд тестов** — `vitest` подключён, но тесты только в `bookcabinet/tests/` (Python, 3 файла).
- **Нет E2E тестов** — для kiosk UI критично перед production.
- **Замусоренный root** — `attached_assets/`, `dist/`, `data/`, `replit.md`, `automation repozitories .zip` (артефакт текущей сессии), `IQRFID-5102_Connection_Guide.md`, `CODE_REVIEW.md`, `design_guidelines.md`. Нужно постепенно ехать в `_archive/` или `docs/`.
- **`replit.md` (13K)** — legacy от Replit-генерации, дублирует README.
- **`uv.lock` + `package-lock.json`** — оба lock'а, OK для гибридного стека, но нужна документация.

## Безопасность

- **Секреты в истории:** ⏭ НЕ ПРОВЕРЕНО — `gitleaks` не установлен в окружении агента. TODO для Vika: запустить `gitleaks detect --source . --log-opts="--all"` с ротацией ключей при находках.
- **`.env.example` существует** — переменные TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IRBIS_*, DATABASE_URL описаны.
- **Уязвимости в зависимостях:** не проверено. Dependabot пока не настроен.
- **Branch protection:** не подтверждено (требует GitHub admin прав).
- **GitHub Security Features (Dependabot alerts, secret scanning, CodeQL):** не подтверждены.

---

## План работ

### P0 — блокеры безопасности
- [ ] Запустить gitleaks на всю историю (issue для Vika)
- [ ] Включить Dependabot alerts + secret scanning + CodeQL (issue для Vika)
- [ ] Создать `LICENSE` (MIT)
- [ ] Создать `SECURITY.md`
- [ ] Создать `.github/CODEOWNERS`

### P1 — базовая структура и документация
- [x] AUDIT.md (этот файл)
- [ ] STATE.md, ROADMAP.md, BACKLOG.md
- [ ] `.editorconfig`, `.gitattributes`
- [ ] Структура `docs/` (adr, architecture, runbooks, guides, ai, prompts, context)
- [ ] `docs/README.md` — карта
- [ ] `docs/ai/*` — правила для AI
- [ ] `docs/context/PRODUCT_CONTEXT.md`, `docs/context/DOMAIN.md`
- [ ] CLAUDE.md — добавить секцию "Источник правды"

### P2 — CI/CD, автоматизация
- [ ] Issue templates + PR template
- [ ] setup-labels.sh + issue для Vika
- [ ] Адаптировать ci-pr.yml под Node 20 + Python 3.11
- [ ] deploy-staging.yml, deploy-prod.yml, release-please.yml, labeler.yml
- [ ] Dependabot config
- [ ] `.pre-commit-config.yaml`
- [ ] Workflow-ы автоматизации (8 шт.)
- [ ] Скрипты автоматизации (9 шт.)
- [ ] Branch protection (issue для Vika)
- [ ] GitHub Environments (issue для Vika)

### P3 — дашборд и качество
- [ ] `tools/dashboard/` стартер
- [ ] `dashboard-fetch.mjs` + workflow
- [ ] GitHub Pages (issue для Vika)
- [ ] Декомпозиция `kiosk.tsx` (отложено, не в этом PR)
- [ ] Frontend тесты (отложено)

---

## Открытые вопросы для founders

- **Лицензия?** README говорит MIT — закладываем MIT (Rivega42 and contributors, 2026). Подтвердить.
- **Стратегия веток?** Сейчас работа в `chore/*`, `feat/*`, `claude/*`. Нужно зафиксировать в `CONTRIBUTING.md`.
- **Запретные зоны для авто-исполнителей?** `bookcabinet/config.py` (GPIO map), `tools/corexy_*.py`, `tools/homing_pigpio.py` — менять только с подтверждением Roman после live cabinet session.
- **Telegram chat_id для уведомлений?** Уже в `.env.example` (`TELEGRAM_CHAT_ID`), но конкретное значение для prod-канала не задокументировано.
- **URL staging/prod?** prod = Raspberry Pi на шкафу в библиотеке (локальный). Staging — нет ли отдельной dev-Pi?

---

## Статусы по шагам

| Шаг | Статус | Комментарий |
|---|---|---|
| 1. AUDIT | ✅ | этот документ |
| 2. Базовая документация | ✅ | STATE/ROADMAP/BACKLOG/SECURITY/LICENSE/.editorconfig/.gitattributes + CLAUDE §0 |
| 3. Структура директорий | ✅ | docs/{adr,architecture,api,runbooks,guides,ai,prompts,context}, infra/, _archive/, tools/dashboard/, .github/CODEOWNERS |
| 4. Правила для AI | ✅ | docs/ai/{CLAUDE_CODE,CLAUDE_DESIGN,VIKA,DEVOPS,EXTERNAL_TASKS,AUTOMATION}.md |
| 5. Контекст для AI | ✅ | docs/context/{PRODUCT_CONTEXT,DOMAIN}.md (GLOSSARY уже был) |
| 6. Labels, шаблоны | ✅ | scripts/setup-labels.sh + 6 issue templates + PR template (плейсхолдеры заменены на реальные milestones) |
| 7. CI/CD | ✅ | ci-pr.yml адаптирован под Node 20 + Python 3.11; ci.yml → ci-legacy.yml (триггеры отключены); deploy-staging/prod, release-please, labeler, dependabot, .pre-commit-config |
| 8. Автоматизация | ✅ | 8 workflow + 9 mjs scripts + setup-project.sh |
| 9. Дашборд | ✅ | tools/dashboard/README.md + scripts/dashboard-fetch.mjs + dashboard-sync.yml |
| 10. Безопасность и финал | ✅ | LICENSE, SECURITY.md, CODEOWNERS, gitleaks ⏭ (не установлен — issue для Vika); итог в STATE.md |

Легенда: ✅ done · 🔄 в процессе · ⏸ не начато · ⏭ пропущено (с причиной)

---

## Финальные итоги (2026-04-30)

### Сделано в этом PR

- 10 коммитов на ветке `chore/repo-setup`.
- Базовая документация проекта оформлена.
- AI-правила и контекст зафиксированы.
- CI/CD workflow-ы готовы (адаптированы под актуальный гибридный стек Node 20 + Python 3.11).
- Автоматизация для Project v2 готова, ждёт активации (issue для Vika).
- Дашборд скаффолд + workflow готовы, ждёт активации Pages (issue для Vika).
- LICENSE добавлен (MIT).
- SECURITY.md, CODEOWNERS, .editorconfig, .gitattributes созданы.
- Существующие docs/, CLAUDE.md, CHANGELOG, README — не изменены деструктивно.

### Issues для Vika (10 шт.) — собраны в `/tmp/vika_issues.md`

1. Применить лейблы (P1)
2. Создать GitHub Project v2 (P1)
3. Branch protection для main (P0)
4. GitHub Environments staging+production (P1)
5. GitHub Pages для дашборда (P2)
6. GitHub Security Features (P0)
7. gitleaks scan на истории (P0)
8. [META] Финальный обход (P1)
9. [META] DevOps настройки от Vika
10. [META] Подтвердить лицензию + секреты

### Что осталось вне PR

- gitleaks scan — не запущен (binary недоступен в окружении агента).
- Активация Vika issues — после merge.
- Декомпозиция `client/src/pages/kiosk.tsx` (2372 строки) — отдельная задача (Q3 2026 по ROADMAP).
- Frontend tests — отдельная задача.
- Адаптация существующих docs (HARDWARE.md устаревший про шторки) — отдельный PR.

### Open questions for founders

См. раздел "Открытые вопросы для founders" выше.
