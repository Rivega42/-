# Architecture

Сюда складываются диаграммы и описания подсистем.

## Что класть

- C4 диаграммы (Context, Container, Component).
- Sequence diagrams для критичных потоков (issue/return book, homing, ИРБИС sync).
- Описания слоёв: hardware drivers, mechanics, services, server, client.
- State machines (issue flow, return flow, error recovery).

## Текущие большие документы

Пока централизованные диаграммы живут в:
- `../HARDWARE.md` — physical layer.
- `../FRONTEND_BACKEND_INTEGRATION.md` — software layers.
- `../ESP32_ARCHITECTURE.md` — variant с ESP32.
- `../IRBIS_INTEGRATION.md` — внешняя интеграция.

По мере роста — выделять подсистемы в отдельные файлы здесь.

## Конвенции

- Диаграммы как Mermaid в md-файлах (предпочтительно), либо svg/png + исходник.
- Каждый файл — одна подсистема или один поток.
- Имя файла: `kebab-case.md`.
