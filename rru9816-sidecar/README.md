# RRU9816 Sidecar Bridge

Этот C# sidecar обеспечивает связь между RRU9816 устройством и Node.js приложением через WebSocket.

## 🔧 Установка и сборка

### 1. Скопируйте RRU9816.dll
```bash
# Скопируйте RRU9816.dll в эту папку
copy path\to\RRU9816.dll .\RRU9816.dll
```

### 2. Сборка приложения
```bash
dotnet build --configuration Release
```

### 3. Запуск
```bash
dotnet run
```

## 📡 WebSocket API

Sidecar создает WebSocket сервер на `ws://localhost:8081/`

### Входящие команды:
```json
{
  "command": "connect",
  "port": "COM15",
  "baudRate": 57600
}

{
  "command": "disconnect"
}

{
  "command": "start_inventory"
}

{
  "command": "stop_inventory"
}
```

### Исходящие события:
```json
{
  "type": "connected",
  "port": "COM15",
  "baudRate": 57600,
  "message": "RRU9816 connected successfully via DLL"
}

{
  "type": "tag_read",
  "epc": "304DB75F1960001300027002",
  "rssi": -42.3,
  "timestamp": "2025-09-18T20:30:45.123Z",
  "readerType": "RRU9816"
}

{
  "type": "error",
  "message": "Connection failed: Invalid port"
}
```

## 🎯 Использование

1. Запустите sidecar: `dotnet run`
2. Sidecar создаст WebSocket сервер на порту 8081
3. Node.js приложение подключится автоматически
4. Все команды RRU9816 будут обрабатываться через DLL

## 📋 Зависимости

- .NET 6.0
- RRU9816.dll (из демки)
- Newtonsoft.Json