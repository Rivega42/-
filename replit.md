# RFID Library Self-Service Kiosk

## Overview
Веб-приложение для автоматического шкафа книговыдачи в библиотеке. Система управляет 126-ячеечным шкафом (2 ряда × 3 колонки × 21 позиция) с тремя ролями пользователей (читатели, библиотекари, администраторы), интеграцией RFID для книг и читательских билетов, mock-интеграцией с IRBIS64 и полной симуляцией механических операций шкафа.

## User Preferences
Preferred communication style: Simple, everyday language (Русский).

## System Architecture

### UI/UX Decisions
- Touch-оптимизированный интерфейс для экрана 1920×1080
- Кнопки высотой 56-80px для удобства касания
- shadcn/ui + TailwindCSS для компонентов
- Анимации active:scale для обратной связи

### Technical Implementations

**Роли пользователей:**
- **Читатель**: забрать забронированные книги, вернуть книги
- **Библиотекарь**: загрузка книг, изъятие возвращённых, инвентаризация
- **Администратор**: все функции + настройки, диагностика

**Cabinet Service (server/services/cabinetService.ts):**
- Симуляция механики: перемещение лотка, открытие/закрытие ячеек
- Настраиваемые таймауты: move (1500ms), tray (800ms), cell (1000ms)
- События: state_changed, operation_started/completed/failed, book_detected
- Полная цепочка операций: reserve → issue → return → extract

**API Endpoints:**
| Endpoint | Описание |
|----------|----------|
| `POST /api/auth/card` | Авторизация по читательскому билету |
| `POST /api/reserve` | Бронирование книги |
| `POST /api/issue` | Выдача книги читателю |
| `POST /api/return` | Возврат книги |
| `POST /api/load-book` | Загрузка книги в шкаф (библиотекарь) |
| `POST /api/extract` | Изъятие книги из ячейки |
| `POST /api/extract-all` | Изъятие всех возвращённых книг |
| `POST /api/run-inventory` | Запуск инвентаризации |

### Project Structure
```
/client                   # React frontend
  /src/pages
    - kiosk.tsx          # Киоск самообслуживания
    - admin.tsx          # Административная панель
/server
  /services
    - cabinetService.ts  # Логика механики шкафа
    - irbisService.ts    # Mock интеграция IRBIS64
    - rfidService.ts     # RFID читатели
  - routes.ts            # API endpoints
  - storage.ts           # In-memory хранилище
/shared
  - schema.ts            # Типы и схемы данных
```

### WebSocket Events
- `cabinet_state` - текущее состояние шкафа
- `operation_started/completed/failed` - жизненный цикл операций
- `book_detected` - обнаружение книги на лотке
- `tag_read`, `card_read` - события RFID

## Design Decisions
- **In-memory storage** вместо SQLite для разработки
- **Mock IRBIS64** для тестирования без реальной библиотечной системы
- **Симуляция механики** с реалистичными задержками для демонстрации
- **WebSocket** для real-time обновлений состояния

## External Dependencies
- React 18, TypeScript, Vite, TailwindCSS
- shadcn/ui, Radix UI, TanStack Query
- Express.js, WebSocket (ws)
- lucide-react для иконок
