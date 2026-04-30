# API Documentation

Главный документ — [`../API.md`](../API.md) (REST API спецификация).

## Что класть в эту папку

По мере роста API — детальные references по подсистемам:
- `irbis-client.md` — клиент для ИРБИС.
- `rfid-protocol.md` — описание протоколов RFID-ридеров.
- `motion-api.md` — внутренний API для моторики.
- `kiosk-api.md` — публичный API для kiosk UI.

## Конвенции

- OpenAPI / JSON Schema, если есть — рядом с .md файлом.
- Примеры запросов / ответов в curl или httpie.
- Версионирование endpoint'ов отмечать явно.
