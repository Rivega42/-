# infra/

Инфраструктурные конфиги, не относящиеся к коду приложения.

## Что класть

- Terraform / Pulumi (если появятся облачные ресурсы).
- Ansible playbook'и для подготовки Raspberry Pi.
- systemd unit-файлы (сейчас живут в `../deploy/`, можно мигрировать).
- nginx / reverse proxy конфиги (если появятся).
- Network diagrams / физическая инфраструктура библиотеки.
- Secrets templates (не сами секреты).

## Текущее состояние

- systemd units — в `../deploy/` (`bookcabinet-daemon.service`, `bookcabinet-ui.service`, `chromium-kiosk.service`, `bookcabinet-calibration.service`).
- `../deploy/install.sh` — установочный скрипт для Pi.

При расширении инфры — переносить сюда с обновлением путей в коде/документации.
