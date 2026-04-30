# 🤖 Автоматизация репозитория

> Источник правды: GitHub Project v2 + лейблы + sub-issues API.
> Все скрипты автоматизации в `scripts/automation/`, workflow-ы в `.github/workflows/`.

## Содержание

- [Архитектура](#архитектура)
- [State machine задач](#state-machine-задач)
- [Workflow-ы и что они делают](#workflow-ы-и-что-они-делают)
- [GitHub Project v2: поля и опции](#github-project-v2-поля-и-опции)
- [Иерархия issues](#иерархия-issues)
- [Зависимости между issues](#зависимости-между-issues)
- [Что требует ручного вмешательства](#что-требует-ручного-вмешательства)
- [Секреты и переменные](#секреты-и-переменные)
- [Отладка](#отладка)

## Архитектура

```
Действие в issue/PR → GitHub Webhook → GitHub Action → scripts/automation/*.mjs → Project v2 API
                                                                                ↓
                                                    Дашборд (раз в час)  ← snapshot.json
                                                                                ↓
                                                        Telegram + Discussions ← weekly digest
```

Каждое изменение в issue или PR триггерит соответствующий workflow, который
вызывает скрипт-обработчик. Скрипт читает структурированные данные из body,
лейблов и Project полей, обновляет состояние и нотифицирует.

## State machine задач

```
                ┌──────────┐
                │  opened  │
                └────┬─────┘
                     │
                     ▼
              ┌────────────┐
              │   Бэклог   │ ◄──────┐
              └─────┬──────┘        │ reopened
                    │ assignee назначен или P0/P1
                    ▼
          ┌────────────────────┐
          │  Готово к работе   │
          └─────────┬──────────┘
                    │ ветка создана / лейбл "статус: в работе"
                    ▼
              ┌────────────┐
              │  В работе  │
              └─────┬──────┘
                    │ PR opened с "Closes #N"
                    ▼
              ┌────────────┐
              │  На ревью  │
              └─────┬──────┘
                    │ PR merged
                    ▼
              ┌──────────┐
              │  Готово  │
              └─────┬────┘
                    │ +14 дней
                    ▼
            ┌────────────────┐
            │ Заархивировано │
            └────────────────┘
```

Ручные переходы через лейблы тоже работают — Actions подхватят и синхронизируют Project.

## Workflow-ы и что они делают

| Workflow | Триггер | Скрипт | Что делает |
|---|---|---|---|
| `auto-labels.yml` | issues/PR любые | `auto-labels.mjs` | Синхронизирует Status в Project и лейблы |
| `sub-issue-rollup.yml` | closed/reopened issue, merged PR | `rollup.mjs` | Пересчитывает Progress эпика, переоткрывает эпик с открытыми subs |
| `epic-board-sync.yml` | epic issues, schedule 6h | `epic-sync.mjs` | Поддерживает Project Epic поле и ROADMAP.md |
| `dependency-resolver.yml` | issues opened/edited/closed | `deps.mjs` | Парсит "Зависит от: #N", разблокирует |
| `validate-issue.yml` | issues opened/edited | `validate.mjs` | Требует обязательные поля |
| `weekly-digest.yml` | schedule MON 9:00 | `digest.mjs` | Постит еженедельный отчёт |
| `stale-cleanup.yml` | schedule 3:00 | actions/stale@v9 | Помечает stale, закрывает через 30д |
| `notifications.yml` | P0 events, PR reviews | `notify.mjs` | Telegram алерты |
| `ci-pr.yml` | pull_request | — | Lint, type-check, test, build, gitleaks, CodeQL |
| `deploy-staging.yml` | push main | — | Авто-деплой staging |
| `deploy-prod.yml` | tag v* | — | Manual approval + prod deploy |
| `release-please.yml` | push main | — | Автогенерация CHANGELOG и releases |
| `labeler.yml` | pull_request | — | Лейблы по путям и размеру |
| `dashboard-sync.yml` | hourly + events | `dashboard-fetch.mjs` | Снепшот для дашборда |

## GitHub Project v2: поля и опции

| Поле | Тип | Опции / Назначение |
|---|---|---|
| `Status` | single-select | Бэклог, Discovery, Готово к работе, В работе, На ревью, Готово, Заблокировано, Заархивировано |
| `Priority` | single-select | P0, P1, P2, P3 |
| `Size` | single-select | XS (4ч), S (1д), M (3д), L (1н), XL (>1н) |
| `Sprint` | iteration | 2-недельные итерации, авто |
| `Batch` | single-select | v0.1.0, v0.2.0, ... (синк с milestones) |
| `Epic` | single-select | EPIC-1, EPIC-2, ... |
| `Stream` | single-select | Платформа, Продукт, Инфра, AI, Команда |
| `Component` | single-select | web, mobile, api, db, devops, ui-kit, ai, integrations |
| `Start date` | date | Из milestone start |
| `Target date` | date | Из milestone due |
| `Progress` | number | % закрытых sub-issues, авто |
| `Blocked by` | text | Список номеров блокирующих |

**Native Project workflows** (включаются в UI):
- ✅ Auto-add to project — все issues и PR репо
- ✅ Item closed → Status: Готово
- ✅ Pull request merged → linked issue: Готово
- ✅ Auto-archive items со статусом Готово старше 14 дней

## Иерархия issues

Используется **native Sub-issues API** (GitHub Sub-issues GA с 2025).

```
Эпик (EPIC-3)
├── Issue #142 (фича M-размера)
│   ├── Sub-issue #142.1 (XS)
│   ├── Sub-issue #142.2 (XS)
│   └── Sub-issue #142.3 (S)
├── Issue #143 (фича S-размера)
└── Issue #144 (баг M-размера)
```

При закрытии sub-issue автоматически пересчитывается `Progress` родителя.
Эпик нельзя закрыть, пока есть открытые sub-issues — `rollup.mjs` переоткроет.

## Зависимости между issues

В body issue:

```
## Зависит от
#140, #141

## Блокирует
#150
```

`deps.mjs` парсит это и:
- Записывает `Blocked by` в Project
- Если есть незакрытые блокеры → лейбл `статус: заблокировано`
- При закрытии #140 → комментирует во все зависящие issues

## Что требует ручного вмешательства

Этого автоматизация не делает (специально, для безопасности):

- **Создание Project v2 и его полей** — через `scripts/setup-project.sh` (issue для Вики)
- **Включение Native Project workflows** — через UI Project'а (issue для Вики)
- **Создание GitHub Environments** (staging, production) — issue для Вики
- **Branch protection** для main — issue для Вики
- **Включение Security Features** (Dependabot, Secret scanning, CodeQL) — issue для Вики
- **GitHub Pages** для дашборда — issue для Вики
- **Создание PAT** с правами `repo + project + read:org` — у founders/Вики
- **Назначение CODEOWNERS** — решает руководитель
- **Изменение веток-исключений** для stale — решает руководитель
- **Telegram bot и chat_id** — у founders

Все эти задачи оформляются как issues с лейблом `для: вики` и тегом `[devops:vika]` в title.

## Секреты и переменные

### GitHub Secrets (per-repo)
| Секрет | Назначение | Кто создаёт |
|---|---|---|
| `PROJECT_TOKEN` | PAT с правами repo + project + read:org | founders |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота | Вика |
| `TELEGRAM_CHAT_ID` | ID канала для уведомлений | founders |

### GitHub Variables (per-repo)
| Переменная | Назначение |
|---|---|
| `PROJECT_NUMBER` | Номер Project v2 |
| `PROJECT_OWNER` | Owner проекта (org или user) |
| `STAGING_URL` | URL staging для smoke tests |
| `PROD_URL` | URL prod |

### Environment secrets
- `staging` — env-specific deploy keys
- `production` — env-specific deploy keys + manual approval

## Отладка

### Workflow упал
1. Открой Actions → найди упавший run
2. Логи внутри `Run script` step
3. Проверь, что `PROJECT_NUMBER` и `PROJECT_TOKEN` заданы

### Issue не попал в Project
1. Native workflow `Auto-add to project` включён?
2. Если нет — issue для Вики на включение

### Status не обновляется
1. Лейбл соответствует STATUS_MAP в `auto-labels.mjs`?
2. PROJECT_TOKEN имеет права `project`?
3. Поле `Status` в Project имеет нужные опции?

### Прогресс эпика не пересчитался
1. Sub-issues привязаны через native API (не просто чек-лист)?
2. Поле `Progress` в Project существует?
3. Лейбл `тип: эпик` стоит на родителе?

### Telegram молчит
1. `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` в secrets?
2. Бот добавлен в канал и имеет права писать?
3. `chat_id` начинается с `-100` (для каналов)?

## Адаптация под другой репозиторий

1. Скопируй `scripts/automation/` и `.github/` в целевой репо
2. Запусти `bash scripts/setup-labels.sh`
3. Создай issue `[devops:vika] Создать Project v2` со ссылкой на `scripts/setup-project.sh`
4. Запиши `PROJECT_NUMBER`, `PROJECT_OWNER` в GitHub Variables
5. Создай `PROJECT_TOKEN` (PAT) и положи в Secrets
6. Адаптируй опции single-select полей под свой проект (эпики, компоненты)

## Связанные документы

- `REPO_SETUP_PROMPT.md` — главный промпт настройки
- `docs/ai/VIKA_RULES.md` — правила работы Вики
- `docs/ai/CLAUDE_CODE_RULES.md` — правила Claude Code
- `ROADMAP.md`, `BACKLOG.md` — продуктовые артефакты
