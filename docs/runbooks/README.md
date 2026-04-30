# Runbooks

Пошаговые операционные инструкции для on-call / оператора / DevOps.

## Существующие runbooks

- [`../DISASTER_RECOVERY.md`](../DISASTER_RECOVERY.md) — recovery procedures (главный runbook).
- [`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md) — known issues и фиксы.

> Эти файлы остаются на старых местах, чтобы не ломать ссылки. Новые runbook-и создавай здесь.

## Шаблон

```markdown
# Runbook: <название проблемы>

**Severity:** P0 | P1 | P2
**Owner:** @nick
**Last validated:** YYYY-MM-DD

## Симптомы
Как понять что ты попал именно сюда.

## Pre-checks
1. Проверь X
2. Проверь Y

## Шаги решения
1. ...
2. ...

## Verification
Как убедиться что всё починилось.

## Если не помогло
Эскалация: <кому>, <как>.

## Связанные
- ADR / другие runbook'и / issues.
```

## Что планируем сюда положить

- `runbook-jam-recovery.md` — застрявшая полка/тарелка.
- `runbook-irbis-down.md` — ИРБИС не отвечает.
- `runbook-rfid-failure.md` — ридер не виден.
- `runbook-belt-slip.md` — пропуск шагов / belt slip.
- `runbook-power-loss.md` — питание моргнуло, как восстановить.
