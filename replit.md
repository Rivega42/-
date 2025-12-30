# RFID Reader Dashboard

## Overview

Локальное Windows веб-приложение для интеграции нескольких RFID считывателей разных типов. Приложение обеспечивает мониторинг и управление в реальном времени через веб-интерфейс на localhost. Поддерживает три типа считывателей: RRU9816 (UHF), IQRFID-5102 (UHF), ACR1281U-C (NFC/HF).

## User Preferences

Preferred communication style: Simple, everyday language (Русский).

---

## Поддерживаемые RFID Считыватели

### 1. RRU9816 (UHF RFID Reader)

**Технология подключения:**
```
[Node.js Backend] ←WebSocket→ [C# Sidecar] ←DLL→ [COM Port] ←→ [RRU9816 Reader]
```

**Технические характеристики:**
| Параметр | Значение |
|----------|----------|
| Тип | UHF RFID (860-960 MHz) |
| Протокол | EPC Gen2 / ISO 18000-6C |
| Подключение | COM Port через C# Sidecar Bridge |
| Baud Rate | 57600 |
| Firmware | v03.01 |
| Требования | Windows 10/11, .NET 6.0 Runtime |

**Архитектура взаимодействия:**
1. **Node.js Backend** отправляет JSON команды через WebSocket (ws://localhost:8081)
2. **C# Sidecar** (rru9816-sidecar/) принимает команды и вызывает RRU9816.dll
3. **RRU9816.dll** общается с железом через COM порт
4. Теги возвращаются обратно в JSON формате через WebSocket

**DLL Функции (RWDev.cs):**
```csharp
OpenComPort()           // Открытие COM порта
InventoryBuffer_G2()    // Inventory в буферном режиме (15 параметров)
Inventory_G2()          // Прямой inventory (fallback)
ReadTagBuffer()         // Чтение тегов из буфера
ClearBuffer_G2()        // Очистка буфера
```

**Два режима Inventory:**
1. **Buffer Mode**: `InventoryBuffer_G2` → `ReadTagBuffer` каждые 500ms
2. **Direct Mode (Fallback)**: `Inventory_G2` каждые 200ms (если буфер пустой)

**Параметры Inventory:**
```
QValue=4, Session=1, InAnt=0x01 (antenna 1), Scantime=10
```

---

### 2. IQRFID-5102 (UHF RFID Reader)

**Технология подключения:**
```
[Node.js Backend] ←Serial Port→ [COM Port] ←→ [IQRFID-5102 Reader]
```

**Технические характеристики:**
| Параметр | Значение |
|----------|----------|
| Тип | UHF RFID (860-960 MHz) |
| Протокол | EPC Gen2 |
| Подключение | Прямой Serial Port |
| Baud Rate | 57600 |
| Data Bits | 8 |
| Stop Bits | 1 |
| Parity | None |

**Протокол связи (Reverse-Engineered):**
```
Формат фрейма: [LEN][ADR][CMD][DATA...][CRC_LOW][CRC_HIGH]
```
- **LEN** - длина данных после байта длины (не включает сам LEN)
- **ADR** - адрес устройства (0x00)
- **CMD** - код команды
- **CRC** - CRC-16 (polynomial 0x8408, LSB first)

**Команда Inventory:**
```
Отправка: 04 00 01 DB 4B
          │  │  │  └─ CRC
          │  │  └─ CMD (0x01 = Inventory)
          │  └─ ADR (0x00)
          └─ LEN (4 байта после)
```

**Форматы ответов:**
```
Нет тегов:  05 00 01 FB F2 3D
                     └─ Status 0xFB = "No tags"

Тег найден: 13 00 01 01 01 0C [12 bytes EPC] [CRC]
                  │  │  │  └─ EPC Length (12 bytes)
                  │  │  └─ RSSI
                  │  └─ Tag Count
                  └─ CMD
```

**Алгоритм CRC-16:**
```javascript
Polynomial: 0x8408
Initial: 0xFFFF
LSB First (Little Endian)
```

**Логика считывания:**
- Polling каждые 500ms через setInterval
- Прямой опрос без буферизации

---

### 3. ACR1281U-C (NFC/HF Reader)

**Технология подключения:**
```
[Node.js Backend] ←PC/SC API→ [Smart Card Service] ←USB→ [ACR1281U-C Reader]
```

**Технические характеристики:**
| Параметр | Значение |
|----------|----------|
| Тип | NFC/HF (13.56 MHz) |
| Протокол | ISO 14443A/B, MIFARE, FeliCa |
| Подключение | PC/SC (Personal Computer/Smart Card) |
| Интерфейс | USB |
| Требования | Windows Smart Card Service |

**Особенности:**
- Использует системный PC/SC API вместо прямого serial port
- Автоматическое определение карт через Smart Card Service
- Поддержка MIFARE Classic, MIFARE Ultralight, NTAG и других NFC форматов

**Логика считывания:**
- PC/SC автоматически обнаруживает карты при поднесении
- Нет необходимости в polling - событийная модель

---

## Сравнение паттернов считывания

| Параметр | RRU9816 | IQRFID-5102 | ACR1281U-C |
|----------|---------|-------------|------------|
| **Транспорт** | WebSocket + DLL | Serial Port | PC/SC API |
| **Формат данных** | JSON | Binary + CRC | PC/SC Events |
| **Режимы работы** | Buffer + Direct | Direct polling | Event-driven |
| **Polling** | 500ms / 200ms | 500ms | Автоматический |
| **Сложность** | Высокая | Средняя | Низкая |
| **Зависимости** | .NET 6.0, DLL | serialport lib | Smart Card Service |

---

## Архитектура системы

### Общая схема
```
┌─────────────────────────────────────────────────────────────────────┐
│                        WEB BROWSER (localhost:5000)                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │     React Frontend (Vite + TypeScript + TailwindCSS)        │   │
│  │     • Dashboard с тегами и логами                            │   │
│  │     • WebSocket для real-time обновлений                     │   │
│  │     • TanStack Query для данных                              │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
└──────────────────────────────│──────────────────────────────────────┘
                               │ HTTP + WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EXPRESS.JS BACKEND (Node.js + TypeScript)         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  RfidService (server/services/rfidService.ts)               │   │
│  │  • Маршрутизация по типу ридера                              │   │
│  │  • EventEmitter для событий тегов                            │   │
│  └───────┬─────────────────────┬─────────────────────┬─────────┘   │
│          │                     │                     │              │
│          ▼                     ▼                     ▼              │
│    ┌───────────┐        ┌───────────┐         ┌───────────┐        │
│    │ WebSocket │        │Serial Port│         │ PC/SC     │        │
│    │ Client    │        │ Direct    │         │ Service   │        │
│    └─────┬─────┘        └─────┬─────┘         └─────┬─────┘        │
└──────────│────────────────────│─────────────────────│───────────────┘
           │                    │                     │
           ▼                    ▼                     ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │ C# Sidecar   │     │   COM Port   │     │ Smart Card   │
    │ (ws:8081)    │     │   Direct     │     │ Service      │
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                     │
           ▼                    ▼                     ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │ RRU9816.dll  │     │ IQRFID-5102  │     │ ACR1281U-C   │
    └──────┬───────┘     └──────────────┘     └──────────────┘
           │                                         
           ▼                                         
    ┌──────────────┐                                 
    │   RRU9816    │                                 
    │   Hardware   │                                 
    └──────────────┘                                 
```

### Технологический стек

**Frontend:**
| Технология | Назначение |
|------------|------------|
| React 18 | UI Framework |
| TypeScript | Типизация |
| Vite | Сборка и HMR |
| TailwindCSS | Стилизация |
| shadcn/ui + Radix UI | Компоненты |
| TanStack Query | Кэширование данных |
| Wouter | Роутинг |
| WebSocket | Real-time обновления |

**Backend:**
| Технология | Назначение |
|------------|------------|
| Node.js | Рантайм |
| Express.js | Web Framework |
| TypeScript | Типизация |
| ws | WebSocket сервер |
| serialport | Serial Port коммуникация |
| EventEmitter | События тегов |

**Sidecar (RRU9816):**
| Технология | Назначение |
|------------|------------|
| C# / .NET 6.0 | Рантайм |
| WebSocket | Связь с Node.js |
| DllImport | Вызовы RRU9816.dll |

**Хранение данных:**
- In-memory storage (без базы данных)
- Сессионное хранение тегов и логов

---

## Структура проекта

```
/
├── client/                      # Frontend (React)
│   ├── src/
│   │   ├── components/         # UI компоненты
│   │   ├── pages/              # Страницы приложения
│   │   ├── hooks/              # React hooks
│   │   └── lib/                # Утилиты
│   └── index.html
│
├── server/                      # Backend (Express)
│   ├── services/
│   │   ├── rfidService.ts      # Главный RFID сервис
│   │   └── pcscService.ts      # PC/SC для ACR1281U-C
│   ├── routes.ts               # API endpoints
│   ├── storage.ts              # In-memory хранение
│   └── index.ts                # Entry point
│
├── rru9816-sidecar/            # C# Bridge для RRU9816
│   ├── Program.cs              # WebSocket сервер + DLL логика
│   ├── RWDev.cs                # DLL функции импорт
│   └── RRU9816.dll             # Драйвер ридера
│
├── shared/
│   └── schema.ts               # Общие типы данных
│
└── IQRFID-5102_Connection_Guide.md  # Инструкция IQRFID-5102
```

---

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /api/ports | Список COM портов |
| POST | /api/connect | Подключение к ридеру |
| POST | /api/disconnect | Отключение |
| GET | /api/status | Статус подключения |
| GET | /api/tags | Список считанных тегов |
| GET | /api/logs | Системные логи |
| DELETE | /api/tags | Очистка тегов |
| DELETE | /api/logs | Очистка логов |

**WebSocket:** `ws://localhost:5000/ws`
- События: `tag_read`, `status`, `log`

---

## Запуск на Windows

1. **Установить зависимости:**
   ```bash
   npm install
   ```

2. **Для RRU9816 - собрать и запустить Sidecar:**
   ```bash
   cd rru9816-sidecar
   dotnet build
   dotnet run
   ```

3. **Запустить приложение:**
   ```bash
   npm run dev
   ```

4. **Открыть в браузере:** http://localhost:5000

---

## Troubleshooting

### RRU9816
- Убедитесь что .NET 6.0 установлен
- Sidecar должен быть запущен ДО подключения
- Проверьте что COM порт не занят другим приложением

### IQRFID-5102
- Baud rate должен быть 57600 (не 115200!)
- Если нет ответа - проверьте питание ридера
- Ридер должен пикнуть при обнаружении карты

### ACR1281U-C
- Убедитесь что Smart Card Service запущен (Windows Service)
- Драйверы ACR должны быть установлены
- Ридер определяется как PC/SC устройство
