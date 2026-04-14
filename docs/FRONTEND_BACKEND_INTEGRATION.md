# BookCabinet — Интеграция фронтенда с бэкендом

## Архитектура

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   React UI  │◄──────────────────►│  Python API │
│   (Kiosk)   │     REST API       │  (aiohttp)  │
└─────────────┘                    └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
              ┌─────▼─────┐        ┌──────▼──────┐       ┌──────▼──────┐
              │   ИРБИС   │        │   SQLite    │       │  Hardware   │
              │ 172.29.67 │        │  (локально) │       │   (GPIO)    │
              └───────────┘        └─────────────┘       └─────────────┘
```

## Механика

### Выдача книги

1. Читатель прикладывает карту → идентификация через ИРБИС
2. Экран "Мои книги":
   - Что на руках (из ИРБИС)
   - Что для него есть в шкафу (из SQLite)
3. Выбор: **[Вернуть книгу]** / **[Взять книгу]**

**Процесс "Взять книгу":**

| # | Действие | Hardware | API |
|---|----------|----------|-----|
| 1 | Пользователь выбирает книгу | - | WS: user_selected_book |
| 2 | Каретка едет к полке | XY motors | POST /api/motion/move |
| 3 | Захват полочки | Tray + Locks | POST /api/tray/grab |
| 4 | Каретка едет к окну 1.2.9 | XY motors | POST /api/motion/move |
| 5 | Открыть внутреннюю шторку | GPIO 3 | POST /api/shutters/inner/open |
| 6 | Задвинуть полочку в окно | Tray | POST /api/tray/extend |
| 7 | Сканировать RFID, проверить книгу | RRU9816 | POST /api/rfid/verify |
| 8 | Закрыть внутреннюю шторку | GPIO 3 | POST /api/shutters/inner/close |
| 9 | Открыть внешнюю шторку | GPIO 2 | POST /api/shutters/outer/open |
| 10 | Экран: "Заберите книгу" | - | WS: take_book_prompt |
| 11 | Ждать 30 сек, сканировать RFID | RRU9816 | WS: book_presence |
| 12a | Книга пропала → ИРБИС: выдана | - | POST /api/book/issue |
| 12b | 30 сек и книга на месте → возврат | - | (процесс возврата) |
| 13 | Закрыть внешнюю шторку | GPIO 2 | POST /api/shutters/outer/close |

### Возврат книги

| # | Действие | Hardware | API |
|---|----------|----------|-----|
| 1 | Пользователь нажимает "Вернуть" | - | WS: return_request |
| 2 | Открыть внешнюю шторку | GPIO 2 | POST /api/shutters/outer/open |
| 3 | Экран: "Положите книгу на полочку" | - | - |
| 4 | Ждать RFID (60 сек таймаут) | RRU9816 | WS: book_detected |
| 5 | Проверить книга из "на руках" | ИРБИС | POST /api/book/verify_return |
| 6 | Закрыть внешнюю шторку | GPIO 2 | POST /api/shutters/outer/close |
| 7 | Открыть внутреннюю шторку | GPIO 3 | POST /api/shutters/inner/open |
| 8 | Забрать полочку внутрь | Tray | POST /api/tray/retract |
| 9 | Закрыть внутреннюю шторку | GPIO 3 | POST /api/shutters/inner/close |
| 10 | Каретка везёт на свободную полку | XY motors | POST /api/motion/move |
| 11 | Отцепить полочку | Locks | POST /api/tray/release |
| 12 | ИРБИС: книга возвращена | - | POST /api/book/return |
| 13 | Экран: "Спасибо! Книга принята" | - | WS: return_complete |

---

## API Endpoints

### Идентификация

```
POST /api/reader/identify
Body: { "card_uid": "304DB75F19600009F0022743" }
Response: {
  "success": true,
  "reader": {
    "name": "Вадим Дмитриевич",
    "ticket": "09 022743",
    "role": "reader",  // reader | librarian | admin
    "books_on_hand": [
      { "rfid": "...", "title": "...", "due_date": "2026-05-14" }
    ]
  },
  "available_in_cabinet": [
    { "rfid": "...", "title": "...", "author": "...", "cell": "1.1.5" }
  ]
}
```

### Книги

```
POST /api/book/lookup
Body: { "rfid": "304DB75F19600009000842FD" }
Response: {
  "success": true,
  "book": {
    "rfid": "...",
    "title": "Клинок молчания",
    "author": "Лэй Ми",
    "year": 2024,
    "status": "in_cabinet",
    "cell": "1.1.5"
  }
}
```

```
POST /api/book/issue
Body: { 
  "reader_uid": "304DB75F19600009F0022743",
  "book_rfid": "304DB75F19600009000842FD"
}
Response: {
  "success": true,
  "due_date": "2026-05-14"
}
```

```
POST /api/book/return
Body: { "book_rfid": "304DB75F19600009000842FD" }
Response: {
  "success": true,
  "message": "Книга принята"
}
```

### Механика

```
POST /api/motion/move
Body: { "cell": "1.1.5" }  // или { "x": 100, "y": 10320 }
Response: { "success": true }

POST /api/tray/grab
Response: { "success": true }

POST /api/tray/release  
Response: { "success": true }

POST /api/tray/extend
Response: { "success": true }

POST /api/tray/retract
Response: { "success": true }

POST /api/shutters/outer/open
POST /api/shutters/outer/close
POST /api/shutters/inner/open
POST /api/shutters/inner/close
Response: { "success": true }
```

### RFID

```
GET /api/rfid/status
Response: {
  "nfc": { "connected": true },
  "uhf_cards": { "connected": true },
  "uhf_books": { "connected": true, "current_tag": "..." }
}

POST /api/rfid/verify
Body: { "expected_rfid": "304DB75F19600009000842FD" }
Response: { 
  "success": true,
  "match": true,
  "detected_rfid": "304DB75F19600009000842FD"
}
```

### Инвентарь шкафа

```
GET /api/cabinet/status
Response: {
  "total_cells": 63,
  "occupied": 12,
  "empty": 48,
  "blocked": 3,
  "cells": [
    { "address": "1.1.1", "status": "occupied", "book_rfid": "...", "book_title": "..." },
    { "address": "1.1.2", "status": "empty" },
    ...
  ]
}

GET /api/cabinet/free_cell
Response: {
  "cell": "1.1.3",
  "x": 100,
  "y": 6510
}
```

---

## WebSocket Events

```
WS /ws/events

// Входящие (от клиента)
{ "type": "subscribe", "events": ["rfid", "motion", "status"] }

// Исходящие (от сервера)
{ "type": "card_read", "source": "nfc", "uid": "304DB75F19600009F0022743" }
{ "type": "card_read", "source": "uhf", "uid": "04239092F17380" }
{ "type": "book_read", "rfid": "304DB75F19600009000842FD" }
{ "type": "book_presence", "present": true, "rfid": "..." }
{ "type": "motion_complete", "cell": "1.2.9" }
{ "type": "shutter_state", "shutter": "outer", "state": "open" }
{ "type": "error", "code": "RFID_MISMATCH", "message": "..." }
```

---

## Экраны фронтенда

### 1. Idle (ожидание)
- "Приложите карту читателя"
- Анимация NFC
- Слушает WebSocket: `card_read`

### 2. Идентификация
- Спиннер "Проверяем карту..."
- Вызов: `POST /api/reader/identify`

### 3. Главный экран (после логина)
- "Здравствуйте, [Имя]!"
- **Мои книги** (на руках) — список с датами возврата
- **Доступно в шкафу** — книги для этого читателя
- Кнопки: **[Взять книгу]** **[Вернуть книгу]**
- Для librarian/admin: **[Режим библиотекаря]**
- Таймаут 60 сек → Idle

### 4. Выдача — процесс
- Прогресс-бар с этапами
- "Получаем книгу..." → "Проверяем..." → "Заберите книгу"
- Таймер 30 сек

### 5. Возврат — ожидание
- "Положите книгу на полочку"
- Таймер 60 сек
- Слушает: `book_read`

### 6. Возврат — процесс
- "Принимаем книгу..."
- Прогресс-бар

### 7. Успех
- Зелёная галочка
- "Книга выдана!" / "Книга принята!"
- Авто-возврат на Idle через 5 сек

### 8. Ошибка
- Красный фон
- Сообщение об ошибке
- **[Начать заново]**

### 9. Режим библиотекаря
- Инвентаризация шкафа
- Загрузка новых книг
- Выгрузка книг
- Диагностика оборудования

---

## Роли и разрешения

| Действие | reader | librarian | admin |
|----------|--------|-----------|-------|
| Взять книгу | ✅ | ✅ | ✅ |
| Вернуть книгу | ✅ | ✅ | ✅ |
| Загрузить книгу | ❌ | ✅ | ✅ |
| Выгрузить книгу | ❌ | ✅ | ✅ |
| Инвентаризация | ❌ | ✅ | ✅ |
| Калибровка | ❌ | ❌ | ✅ |
| Настройки | ❌ | ❌ | ✅ |

Роль определяется по карте в ИРБИС (или локальной таблице `users`).

---

## База данных (SQLite)

### Таблицы (уже есть в models.py)
- `cells` — ячейки шкафа, статус, что лежит
- `books` — книги в шкафу, RFID, статус
- `users` — пользователи (для оффлайн/кэш)
- `operations` — лог операций
- `settings` — настройки

### Синхронизация с ИРБИС
- При выдаче/возврате → обновить ИРБИС + локально
- При старте → сверить локальную БД с ИРБИС (опционально)

---

## Координаты (из calibration.json)

- **Окно выдачи:** `1.2.9`
- **Стойки X:** rack1=100, rack2=10220, rack3=20370
- **Полки Y:** интерполяция по anchors (0-21)
- **Заблокированные:** 1.1.0, 1.2.7-18, и др.

---

## Приоритет реализации

### Фаза 1: Базовая связка
1. ✅ ИРБИС поиск по `"IN={rfid}"` 
2. [ ] API `/api/reader/identify`
3. [ ] API `/api/book/lookup`
4. [ ] WebSocket события считывателей
5. [ ] Фронт: экраны Idle → Идентификация → Главный

### Фаза 2: Выдача (без механики)
6. [ ] API `/api/book/issue` (только ИРБИС)
7. [ ] Фронт: экран выдачи (симуляция)

### Фаза 3: Механика
8. [ ] Заменить замки GPIO 12/13
9. [ ] API motion/tray/shutters
10. [ ] Полный цикл выдачи

### Фаза 4: Возврат
11. [ ] API `/api/book/return`
12. [ ] Полный цикл возврата

### Фаза 5: Режим библиотекаря
13. [ ] Загрузка/выгрузка книг
14. [ ] Инвентаризация
