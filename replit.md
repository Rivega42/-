# RFID Library Self-Service Kiosk (BookCabinet)

## Overview
Система автоматизированной книговыдачи для библиотек на базе Raspberry Pi 4. Управляет шкафом с 126 ячейками (2 ряда × 3 колонки × 21 позиция), поддерживает три роли пользователей (читатель, библиотекарь, администратор), интеграцию RFID для книг (IQRFID-5102) и читательских билетов (ACR1281U-C), mock-интеграцию с IRBIS64.

## User Preferences
Preferred communication style: Simple, everyday language (Русский).

## System Architecture

### Компоненты Python (bookcabinet/)

**Механика (mechanics/):**
- `algorithms.py` - Алгоритмы INIT/TAKE/GIVE с реальным path planning
- `corexy.py` - CoreXY кинематика с расчётом траекторий для 126 ячеек
- `calibration.py` - Калибровочные данные позиций X/Y

**Оборудование (hardware/):**
- `motors.py` - Шаговые моторы CoreXY + лоток
- `servos.py` - Сервоприводы замков
- `shutters.py` - Шторки (внутренняя/внешняя)
- `sensors.py` - Датчики TCST2103 с проверкой концевиков
- `gpio_manager.py` - Управление GPIO через pigpio

**RFID (rfid/):**
- `card_reader.py` - ACR1281U-C для читательских билетов (PC/SC)
- `book_reader.py` - IQRFID-5102 для RFID-меток книг (Serial)

**Бизнес-логика (business/):**
- `auth.py` - Аутентификация с проверкой ролей
- `issue.py` - Выдача книг читателю
- `return_book.py` - Возврат книг
- `load.py` - Загрузка книг (библиотекарь)
- `unload.py` - Изъятие книг

**Сервер (server/):**
- `web_server.py` - aiohttp веб-сервер
- `api_routes.py` - REST API (30+ endpoints)
- `websocket_handler.py` - WebSocket для real-time
- `static/` - Touch-оптимизированный UI 1920×1080

**Мониторинг (monitoring/):**
- `telegram.py` - Уведомления через Telegram Bot API
- `backup.py` - Резервное копирование с ротацией
- `watchdog.py` - Мониторинг состояния

### Роли пользователей

| Роль | Возможности |
|------|-------------|
| **Читатель** | Забрать забронированные книги, вернуть книги |
| **Библиотекарь** | Загрузка книг, изъятие возвращённых, просмотр ячеек, инвентаризация, журнал операций |
| **Администратор** | Все функции + калибровка CoreXY, диагностика оборудования, настройки системы, backup |

### API Endpoints

| Endpoint | Описание |
|----------|----------|
| `POST /api/auth/card` | Авторизация по читательскому билету |
| `POST /api/issue` | Выдача книги читателю |
| `POST /api/return` | Возврат книги |
| `POST /api/load-book` | Загрузка книги в шкаф |
| `POST /api/extract` | Изъятие книги из ячейки |
| `POST /api/extract-all` | Изъятие всех возвращённых книг |
| `POST /api/run-inventory` | Запуск инвентаризации |
| `GET/POST /api/calibration` | Калибровка позиций |
| `GET /api/diagnostics` | Диагностика оборудования |
| `GET/POST /api/settings` | Настройки системы |
| `POST /api/backup/create` | Создание бэкапа |
| `POST /api/test/*` | Тестирование компонентов |

### Path Planning

PathPlanner класс реализует:
- Расчёт координат для 126 ячеек (positions_x, positions_y)
- Построение пути с промежуточными точками
- Избегание диагональных движений
- Оценка времени перемещения

### Безопасность датчиков

- `_safe_move_xy()` - проверка концевиков при движении
- `_safe_tray_extend/retract()` - проверка датчиков лотка
- Аварийная остановка при срабатывании endstops

### Telegram уведомления

- Запуск/остановка системы
- Ошибки и критические события
- Статус ИРБИС
- Заполненность шкафа
- Необходимость изъятия книг

### Резервное копирование

- Автоматическое по расписанию (systemd timer)
- Ротация: 30 дней или 50 бэкапов max
- Включает: база данных + calibration.json
- Метаданные каждого бэкапа

## Развёртывание на Raspberry Pi

```bash
sudo bash bookcabinet/install_raspberry.sh
```

Скрипт настраивает:
- pigpiod, pcscd autostart
- udev правила для RFID (072f:2200)
- Serial порты (UART enabled, console disabled)
- systemd сервисы (bookcabinet, backup timer)
- calibration.json по умолчанию

## Структура проекта

```
/bookcabinet                  # Python backend
  /hardware                   # GPIO, моторы, датчики
  /mechanics                  # Алгоритмы, CoreXY, калибровка
  /rfid                       # Card/Book readers
  /irbis                      # Mock IRBIS64
  /business                   # Бизнес-логика
  /database                   # SQLite
  /server                     # aiohttp + static UI
  /monitoring                 # Telegram, backup
  main.py                     # Entry point
  config.py                   # Конфигурация
  install_raspberry.sh        # Установка
```

## Design Decisions
- **Python + aiohttp** для async операций с оборудованием
- **SQLite** для локального хранения (126 ячеек, операции, логи)
- **Mock режим** для разработки без Raspberry Pi
- **PathPlanner** для реального планирования траекторий CoreXY
- **WebSocket** для real-time обновлений UI

## External Dependencies
- Python 3.9+, aiohttp
- pigpio (GPIO), pyscard (PC/SC), pyserial
- SQLite3
