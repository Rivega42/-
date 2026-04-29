# 📥 RETURN_BOOK_WORKFLOW.md — Цикл возврата книги

Полное ТЗ workflow возврата книги. Источник: GitHub issue #80.

Реализуется в `bookcabinet/workflows/return.py`.

> **Главное отличие от выдачи:** метка ПОЯВЛЯЕТСЯ (а не пропадает), сверка после появления, fallback на свободную ячейку.

---

## Входные параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `expected_book_rfid` | str | RFID метка возвращаемой книги |
| `book_title` | str | Название для экрана |
| `target_address` | str | Куда положить книгу (определяется по каталогу/свободным ячейкам) |
| `window_address` | str | Окно приёма (по умолчанию `1.2.9`) |
| `speed` | int | Скорость каретки (default 2600) |
| `drop_timeout_sec` | int | Таймаут ожидания сдачи книги (default 60) |

---

## Последовательность возврата

| # | Действие | Параллельно |
|---|----------|-------------|
| 1 | Запуск `return_book(rfid, title, target)` | |
| 2 | **Открыть внутреннюю шторку** (~15 сек) | + `goto window` через `asyncio.gather` |
| 3 | Извлечь пустую полочку из окна (`extract_front`) | |
| 4 | Положить обратно в окно (`return_front`) | |
| 5 | **Закрыть внутреннюю шторку** (15 сек) | |
| 6 | **Открыть внешнюю шторку** (15 сек) | |
| 7 | Экран: «Положите книгу: `<title>`» + обратный отсчёт 60 сек | |
| 8 | RFID-опрос каждые 500ms: появилась ли метка? | |
| 9 | Первое из: метка появилась (→ шаг 10) или 60s истекли (→ сценарий Б) | |
| 10 | **RFID-сверка:** считанная метка == `expected_book_rfid`? | |
|    | • Совпадает → шаг 11 | |
|    | • НЕ совпадает → сценарий А | |
| 11 | Экран: «Спасибо! Книга принята. Шторка закроется через 5 сек.» | |
| 12 | Ждём 5 сек (UX: пользователь видит подтверждение) | |
| 13 | **Закрыть внешнюю шторку** (15 сек) | |
| 14 | **Открыть внутреннюю шторку** (15 сек) | |
| 15 | Извлечь полочку с книгой из окна (`extract_front`) | |
| 16 | `goto target_address` | |
| 17 | Положить полочку (`return_front` или `return_rear` по depth) | |
| 18 | **Закрыть внутреннюю шторку** | |
| 19 | Логировать в БД: успешный возврат + обновить catalog (книга на `target_address`) | |

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
    RFID_card->>DB: Авторизация + определение книги для возврата
    DB-->>Screen: Книга для возврата найдена
    Screen->>Cabinet: return_book(rfid, title, target)

    par Параллельно
        Cabinet->>Inner: Открыть (GPIO 3 HIGH, wait 15s)
    and
        Cabinet->>Cabinet: goto window_address
    end

    Cabinet->>Cabinet: extract_front (пустая полочка из окна)
    Cabinet->>Cabinet: return_front (назад в окно)
    Cabinet->>Inner: Закрыть (GPIO 3 LOW, wait 15s)
    Cabinet->>Outer: Открыть (GPIO 2 HIGH, wait 15s)
    Cabinet->>Screen: «Положите книгу: <title>» + 60s таймер

    loop Каждые 500ms
        Cabinet->>RFID_book: Метка появилась?
    end

    alt Метка появилась
        Cabinet->>RFID_book: Считать метку (таймаут 3s)
        alt Метка совпадает
            Cabinet->>Screen: «Спасибо! Книга принята. Закрытие через 5 сек»
            Note over Cabinet: Ждём 5 сек
            Cabinet->>Outer: Закрыть (GPIO 2 LOW, wait 15s)
            Cabinet->>Inner: Открыть (GPIO 3 HIGH, wait 15s)
            Cabinet->>Cabinet: extract_front (полочка с книгой)
            Cabinet->>Cabinet: goto target_address
            Cabinet->>Cabinet: return_front/rear (по depth)
            Cabinet->>Inner: Закрыть (GPIO 3 LOW)
            Cabinet->>DB: Логировать: book_returned, target=target_address
        else Метка НЕ совпадает
            Cabinet->>Screen: «Это не та книга. Заберите и попробуйте снова»
            Note over Cabinet: Ждём ещё 60 сек
            Cabinet->>DB: Логировать WARN: wrong_book_placed
        end
    else 60 секунд истекли
        Cabinet->>Outer: Закрыть (GPIO 2 LOW, wait 15s)
        Cabinet->>DB: Логировать: book_not_returned
        Cabinet->>Bot: Уведомление библиотекарю + пользователю
    end
```

---

## State-диаграмма состояний возврата

```mermaid
stateDiagram-v2
    [*] --> idle: Система готова
    idle --> opening_inner: return_book() вызван
    opening_inner --> moving_to_window: Шторка открыта + goto window
    moving_to_window --> preparing_shelf: extract_front + return_front
    preparing_shelf --> closing_inner: Лоток готов
    closing_inner --> opening_outer: Внутренняя закрыта
    opening_outer --> waiting_drop: Внешняя открыта
    waiting_drop --> rfid_appeared: Метка обнаружена
    waiting_drop --> timeout_no_book: 60 сек без метки
    rfid_appeared --> rfid_check: Сверка метки
    rfid_check --> book_confirmed: Метка совпала
    rfid_check --> wrong_book: Метка НЕ совпала
    book_confirmed --> show_thanks: Экран «Спасибо»
    show_thanks --> closing_outer: 5 секунд паузы
    wrong_book --> waiting_drop: Ждём ещё 60 сек
    timeout_no_book --> closing_outer
    closing_outer --> opening_inner_place: Внешняя закрыта
    opening_inner_place --> placing_book: Внутренняя открыта
    placing_book --> done: Полочка в target_address
    done --> idle
    [*] --> error_rfid_reader: RFID ридер недоступен
    error_rfid_reader --> manual_confirm: Режим ручного подтверждения
```

---

## Flowchart — ошибочные сценарии

```mermaid
flowchart TD
    START([Начало возврата]) --> OPEN_INNER[Открыть внутреннюю шторку]
    OPEN_INNER --> PAR_GOTO{Параллельно: goto window}
    PAR_GOTO --> PREPARE[extract_front + return_front]
    PREPARE --> CLOSE_INNER[Закрыть внутреннюю шторку]
    CLOSE_INNER --> OPEN_OUTER[Открыть внешнюю шторку]
    OPEN_OUTER --> WAIT_DROP{Ждём книгу 60 сек}

    WAIT_DROP -->|Метка появилась| RFID_CHECK{RFID-сверка}
    WAIT_DROP -->|60 сек истекли| NOT_RETURNED[Сценарий Б: не сдана]

    RFID_CHECK -->|Метка совпала| CONFIRM[«Спасибо! Закрытие через 5 сек»]
    RFID_CHECK -->|Метка НЕ совпала| WRONG_BOOK[Сценарий А: не та книга]

    WRONG_BOOK --> SCREEN_ERR[«Это не та книга, заберите»]
    SCREEN_ERR --> WAIT_60[Ждём ещё 60 сек]
    WAIT_60 -->|Исправил| RFID_CHECK
    WAIT_60 -->|Не исправил| NOT_RETURNED

    CONFIRM --> WAIT5[Пауза 5 сек]
    WAIT5 --> CLOSE_OUTER[Закрыть внешнюю шторку]
    CLOSE_OUTER --> OPEN_INNER2[Открыть внутреннюю шторку]
    OPEN_INNER2 --> EXTRACT_BOOK[extract_front с книгой]
    EXTRACT_BOOK --> CHECK_TARGET{Целевая ячейка свободна?}

    CHECK_TARGET -->|Свободна| GOTO_TARGET[goto target_address]
    CHECK_TARGET -->|Занята| FIND_FREE[Сценарий Д: найти свободную]
    FIND_FREE --> GOTO_TARGET

    GOTO_TARGET --> PLACE[return_front/rear]
    PLACE --> CLOSE_INNER2[Закрыть внутреннюю шторку]
    CLOSE_INNER2 --> LOG_DB[Логировать в БД]
    LOG_DB --> DONE([Готово])

    NOT_RETURNED --> CLOSE_OUTER_ERR[Закрыть внешнюю шторку]
    CLOSE_OUTER_ERR --> LOG_ERR[Логировать book_not_returned]
    LOG_ERR --> NOTIFY_TG[Уведомить: библиотекаря + пользователя]
    NOTIFY_TG --> DONE
```

---

## Ошибочные сценарии

### А) Положили не ту книгу (шаг 10)

1. Экран: «Это не та книга. Заберите и попробуйте снова. Номер ошибки: `<error_id>`»
2. **НЕ закрывать** внешнюю шторку — даём 60 сек на исправление
3. Логировать: `system_log WARN`
4. Если за 60 сек не исправили → закрыть, эскалация в Telegram

### Б) Книга не сдана за 60 сек

1. Закрыть внешнюю шторку
2. Логировать: `book_not_returned`
3. Полочка остаётся в окне (повторная попытка возможна)
4. Уведомление пользователю и библиотекарю

### В) RFID-ридер не отвечает

1. Режим `manual_confirm`: пользователь жмёт «Я положил книгу» на экране
2. Эскалация: библиотекарь вручную сверит RFID при следующем приходе
3. Логировать: `rfid_reader_error`

### Д) Целевая ячейка занята

1. **Auto-fallback**: найти ближайшую свободную ячейку через `shelf_data.db`
2. Логировать переадресацию: `target_redirected: original → new`
3. Продолжить как обычно с новым адресом

---

## Зависимости (готовые модули)

| Модуль | Расположение | Статус |
|--------|-------------|--------|
| move_shelf.py | `tools/move_shelf.py` | ✅ Готов |
| shelf_operations.py | `tools/shelf_operations.py` | ✅ Готов |
| shutter.py | `tools/shutter.py` | ✅ Готов |
| book_reader.py | `bookcabinet/rfid/book_reader.py` | ✅ UHF ридер |
| database.py | `bookcabinet/database.py` | ✅ Поиск свободных ячеек |
| websocket_handler.py | `bookcabinet/server/websocket_handler.py` | ✅ Экран |
