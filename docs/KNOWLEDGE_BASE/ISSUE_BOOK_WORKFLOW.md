# 📤 ISSUE_BOOK_WORKFLOW.md — Цикл выдачи книги

Полное ТЗ workflow выдачи книги. Источник: GitHub issue #79.

Реализуется в `bookcabinet/workflows/issue.py`.

---

## Входные параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `source_address` | str | Адрес ячейки-источника, например `2.1.16` |
| `window_address` | str | Адрес окна выдачи (по умолчанию `1.2.9`) |
| `expected_book_rfid` | str | RFID метка ожидаемой книги |
| `book_title` | str | Название книги для экрана |
| `speed` | int | Скорость каретки (default 2600) |
| `pickup_timeout_sec` | int | Таймаут ожидания забора (default 30) |

---

## Последовательность выдачи

| # | Действие | Параллельно |
|---|----------|-------------|
| 1 | Запуск `issue_book(source, window, rfid, title)` | |
| 2 | **Открыть внутреннюю шторку** (GPIO 3→HIGH, wait 15s) | + `goto source` через `asyncio.gather` |
| 3 | Извлечь полочку: `extract_rear` если depth=2, `extract_front` если depth=1 | |
| 4 | `goto window` (внутренняя уже открыта) | |
| 5 | Положить полочку в окно: `return_front` если window_depth=1 | |
| 6 | **Закрыть внутреннюю шторку** (GPIO 3→LOW, wait 15s) | |
| 7 | **RFID-сверка:** book_reader читает метку 3 сек | |
|   | • Совпадает → шаг 8 | |
|   | • НЕ совпадает → сценарий А | |
| 8 | **Открыть внешнюю шторку** (GPIO 2→HIGH, wait 15s) | |
| 9 | Экран: «Заберите книгу: `<title>`» + обратный отсчёт 30 сек | |
| 10 | Опрос каждые 500ms: RFID метка ещё на полке? | |
| 11 | Первое из: метка пропала (→ ждём 5s → шаг 12) или 30s истекли (→ шаг 12) | |
| 12 | **Закрыть внешнюю шторку** (GPIO 2→LOW, wait 15s) | |
| 13 | **Открыть внутреннюю шторку** (GPIO 3→HIGH, wait 15s) | |
| 14 | Извлечь полочку из окна (`extract_front`) | |
| 15 | `goto source` — везём полочку обратно | |
| 16 | Положить полочку в источник (`return_front` или `return_rear` по depth) | |
| 17 | **Закрыть внутреннюю шторку** (GPIO 3→LOW) | |
| 18 | Логировать в БД: успешная выдача + статус (забрана/не забрана) | |

---

## Sequence-диаграмма полного потока

```mermaid
sequenceDiagram
    participant User as Пользователь
    participant Screen as Экран (WebSocket)
    participant Cabinet as Шкаф (motors+tray+locks)
    participant Inner as Шторка внутренняя
    participant Outer as Шторка внешняя
    participant RFID_book as RFID книги (UHF)
    participant RFID_card as RFID карты
    participant DB as База данных
    participant Bot as Telegram бот

    User->>RFID_card: Прикладывает карту
    RFID_card->>DB: Авторизация
    DB-->>Screen: Список заказанных книг
    User->>Screen: Выбирает книгу
    Screen->>Cabinet: issue_book(source, window, rfid, title)

    par Параллельно
        Cabinet->>Inner: Открыть (GPIO 3 HIGH, wait 15s)
    and
        Cabinet->>Cabinet: goto source_address
    end

    Cabinet->>Cabinet: extract (front/rear по depth)
    Cabinet->>Cabinet: goto window_address
    Cabinet->>Cabinet: return_front
    Cabinet->>Inner: Закрыть (GPIO 3 LOW, wait 15s)
    Cabinet->>RFID_book: Читать метку (таймаут 3s)

    alt Метка совпадает
        Cabinet->>Outer: Открыть (GPIO 2 HIGH, wait 15s)
        Cabinet->>Screen: «Заберите книгу: <title>» + 30s таймер
        loop Каждые 500ms
            Cabinet->>RFID_book: Метка на месте?
        end
        alt Метка пропала
            Note over Cabinet: Ждём ещё 5 сек
            Cabinet->>Outer: Закрыть (GPIO 2 LOW, wait 15s)
            Cabinet->>DB: Логировать: book_issued
        else 30 секунд истекли
            Cabinet->>Outer: Закрыть (GPIO 2 LOW, wait 15s)
            Cabinet->>DB: Логировать: book_not_picked_up
            Cabinet->>Bot: Уведомление: не забрали
        end
    else Метка НЕ совпадает
        Cabinet->>DB: Логировать ERROR: rfid_mismatch
        Cabinet->>Screen: «Ошибка. Обратитесь к библиотекарю»
        Cabinet->>Bot: Эскалация с error_id
    end

    Cabinet->>Inner: Открыть (GPIO 3 HIGH, wait 15s)
    Cabinet->>Cabinet: extract_front (из окна)
    Cabinet->>Cabinet: goto source_address
    Cabinet->>Cabinet: return (front/rear по depth)
    Cabinet->>Inner: Закрыть (GPIO 3 LOW)
    Cabinet->>DB: Финальное логирование
```

---

## State-диаграмма состояний выдачи

```mermaid
stateDiagram-v2
    [*] --> idle: Система готова
    idle --> opening_inner: issue_book() вызван
    opening_inner --> moving_to_source: Шторка открыта
    moving_to_source --> extracting: goto source + extract
    extracting --> moving_to_window: Полочка на каретке
    moving_to_window --> placing_in_window: goto window
    placing_in_window --> closing_inner: return_front выполнен
    closing_inner --> rfid_check: Шторка закрыта
    rfid_check --> opening_outer: RFID совпал
    rfid_check --> error_rfid_mismatch: RFID НЕ совпал
    opening_outer --> waiting_pickup: Шторка открыта
    waiting_pickup --> book_taken: Метка пропала (забрали)
    waiting_pickup --> book_not_taken: 30 сек истекли
    book_taken --> closing_outer
    book_not_taken --> closing_outer
    closing_outer --> opening_inner_return: Шторка закрыта
    opening_inner_return --> returning: Шторка открыта
    returning --> done: Полочка в источнике, шторка закрыта
    error_rfid_mismatch --> returning: Возврат полочки без открытия внешней
    done --> idle
    [*] --> error_motion: Ошибка мотора
    error_motion --> manual_recovery
```

---

## Flowchart — ошибочные сценарии

```mermaid
flowchart TD
    START([Начало выдачи]) --> OPEN_INNER[Открыть внутреннюю шторку]
    OPEN_INNER --> GOTO_PARALLEL{Параллельно: goto source}
    GOTO_PARALLEL --> EXTRACT[extract front/rear]
    EXTRACT --> GOTO_WIN[goto window]
    GOTO_WIN --> PLACE[return_front в окно]
    PLACE --> CLOSE_INNER[Закрыть внутреннюю шторку]
    CLOSE_INNER --> RFID_CHECK{RFID-сверка}

    RFID_CHECK -->|Метка совпала| OPEN_OUTER[Открыть внешнюю шторку]
    RFID_CHECK -->|Метка НЕ совпала| ERR_A[Сценарий А]

    OPEN_OUTER --> WAIT_PICKUP{Ждём забора 30 сек}
    WAIT_PICKUP -->|Метка пропала| WAIT5[Ждём 5 сек]
    WAIT_PICKUP -->|30 сек истекли| NOT_PICKED[Книга не забрана]

    WAIT5 --> CLOSE_OUTER[Закрыть внешнюю шторку]
    NOT_PICKED --> NOTIFY_B[Уведомление: не забрана]
    NOTIFY_B --> CLOSE_OUTER

    CLOSE_OUTER --> RETURN_SHELF[Вернуть полочку в источник]

    ERR_A --> LOG_ERR[Лог ERROR: rfid_mismatch]
    LOG_ERR --> SCREEN_ERR[Экран: номер ошибки]
    SCREEN_ERR --> TELEGRAM_ESC[Эскалация в Telegram]
    TELEGRAM_ESC --> RETURN_SHELF

    RETURN_SHELF --> LOG_DB[Логировать в БД]
    LOG_DB --> DONE([Готово])

    GOTO_PARALLEL -->|Ошибка мотора| ERR_C[Сценарий С]
    ERR_C --> ESTOP[Emergency Stop: все моторы]
    ESTOP --> CLOSE_ALL[Закрыть обе шторки]
    CLOSE_ALL --> ESC_TG[Эскалация Telegram + лог]
    ESC_TG --> MANUAL[Режим manual recovery]
```

---

## Ошибочные сценарии

### А) RFID метка не совпала (шаг 7)

1. Логировать в `system_log`: `level=ERROR, source=issue_workflow` — несоответствие метки
2. Экран: «Произошла ошибка при выдаче. Номер ошибки: `<error_id>`. Обратитесь к библиотекарю.»
3. Эскалация в Telegram (`monitoring/telegram.py`)
4. Вернуть полочку в исходную ячейку (шаги 13–17 **без** открытия внешней шторки)

### Б) Книга не забрана за 30 сек

1. Закрыть внешнюю шторку
2. Логировать: `book_not_picked_up` с book_id и user_id
3. Полочка возвращается в исходную ячейку
4. Уведомление в Telegram

### В) Ошибка движения (концевик не сработал, stall)

1. Emergency stop: все моторы остановить
2. Закрыть обе шторки
3. Эскалация в Telegram + журнал `system_log`
4. Шкаф в режим `manual_recovery`

---

## Зависимости (готовые модули)

| Модуль | Расположение | Статус |
|--------|-------------|--------|
| move_shelf.py | `tools/move_shelf.py` | ✅ Готов |
| shelf_operations.py | `tools/shelf_operations.py` | ✅ Готов |
| shutter.py | `tools/shutter.py` | ✅ Готов |
| shutters.py | `bookcabinet/hardware/shutters.py` | ✅ Готов |
| book_reader.py | `bookcabinet/rfid/book_reader.py` | ✅ Есть UHF ридер |
| websocket_handler.py | `bookcabinet/server/websocket_handler.py` | ✅ Для экрана |
