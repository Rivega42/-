# DevOps Rules — общие правила

> Применимо ко всем DevOps-задачам в проекте, независимо от исполнителя (Vika, founders, контрибьюторы).

---

## Принципы

1. **Reproducibility.** Любое infra-изменение должно быть воспроизводимым из репо (script / IaC / документированный runbook).
2. **Least privilege.** Минимальные права для каждого токена / сервис-аккаунта.
3. **Audit trail.** Все изменения через PR или зафиксированные issues. Никаких "molchaшних" изменений в UI GitHub.
4. **Secrets никогда в коде.** Только в GitHub Secrets / `.env` / vault.

## Окружения

| Окружение | Назначение | Деплой | Approval |
|---|---|---|---|
| `dev` | локальная разработка | вручную | — |
| `staging` | dev-Pi или CI sandbox | auto от `develop` (если есть) | — |
| `production` | реальный шкаф в библиотеке | manual + tag `v*` | founders |

## Branch protection (main)

- Required PR review: 1 (CODEOWNERS обязательно).
- Required status checks: `ci-pr / lint`, `ci-pr / type-check`, `ci-pr / test`, `ci-pr / build`, `gitleaks`, `validate-issue`.
- Linear history.
- Запрет force-push.
- Запрет deletion.
- Required conversation resolution.

(Применение — через issue для Vika, см. `VIKA_RULES.md`.)

## Secrets rotation policy

| Секрет | Период | Триггер ротации |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | 6 мес | подозрение на leak |
| `IRBIS_*` | по запросу библиотеки | смена пароля у них |
| `PROJECT_TOKEN` (GitHub PAT) | 90 дней | expiration |
| Любой при leak | немедленно | gitleaks alert |

## Releases

- `release-please` управляет CHANGELOG и версией.
- Tags: `v<MAJOR>.<MINOR>.<PATCH>` (semver).
- Production deploy только с tag.
- Pre-release: `v1.2.3-rc.1` для staging.

## Backup

- БД — `bookcabinet/data/*.db` — ежедневный snapshot на Pi.
- Calibration — `calibration.json` в репо + бэкап на Pi.
- ИРБИС не бэкапим (это их система).

## Monitoring

- `journalctl -u bookcabinet -f` — главный лог.
- Telegram alerts при:
  - сбое systemd unit (auto-restart исчерпан),
  - jam'е (мотор не дошёл за timeout),
  - ИРБИС down,
  - low disk / high CPU.

## Disaster Recovery

См. `docs/DISASTER_RECOVERY.md`.

## Подготовка нового Pi

См. (TODO) `docs/guides/setup-pi.md`. Пока что — `bookcabinet/install_raspberry.sh` + `deploy/install.sh`.

## CI/CD ownership

- Workflow-ы — read-only для разработчиков, write только для CODEOWNERS (`@Rivega42`).
- Изменения в `.github/workflows/` требуют явного approval.
- Self-hosted runner (если появится) — настройка через issue для Vika.
