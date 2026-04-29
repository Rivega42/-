# 🚀 STARTUP.md — Старт системы BookCabinet

Что происходит от включения питания до готовности шкафа к работе.

---

## Цепочка запуска

```
Включение питания
    └── systemd → bookcabinet.service
        └── python3 /home/admin42/bookcabinet/main.py
            ├── startup_checks()       — проверка всех подсистем
            ├── StartupRecovery.run()  — восстановление после аварий
            └── aiohttp app.start()   — веб-сервер + WebSocket
```

---

## systemd service

Файл: `/etc/systemd/system/bookcabinet.service`

```ini
[Unit]
Description=BookCabinet Controller
After=network.target pigpiod.service

[Service]
User=admin42
WorkingDirectory=/home/admin42/bookcabinet
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5s
Environment=PYTHONPATH=/home/admin42/bookcabinet

[Install]
WantedBy=multi-user.target
```

Управление:
```bash
sudo systemctl start bookcabinet
sudo systemctl stop bookcabinet
sudo systemctl status bookcabinet
journalctl -u bookcabinet -f   # логи в реальном времени
```

---

## startup_checks() — проверка подсистем

Файл: `bookcabinet/main.py`

Последовательность проверок:

| Подсистема | Что проверяется | При ошибке |
|------------|----------------|------------|
| База данных | Подключение к `shelf_data.db` | Логировать ERROR, продолжить |
| GPIO / pigpio | `pigpio.pi()` connection | Остановить запуск |
| RFID card reader | `/dev/pcsc` или `/dev/ttyUSB1` | Логировать WARN, mock_mode |
| RFID book reader | `/dev/ttyUSB2` | Логировать WARN, mock_mode |
| ИРБИС | TCP соединение 172.29.67.70:6666 | Логировать WARN, mock_mode |

В режиме `MOCK_MODE=true` (env) проверки RFID/GPIO пропускаются — для тестирования без железа.

---

## StartupRecovery — восстановление после аварий

Класс: `bookcabinet/monitoring/watchdog.py::StartupRecovery`

Запускается **один раз** при старте приложения (`on_startup`).

### Последовательность StartupRecovery

```python
class StartupRecovery:
    async def run(self):
        # 1. Закрыть обе шторки (на всякий случай)
        await shutters.close_both()
        
        # 2. Retract tray — СЛЕПЫЕ 3000 ШАГОВ!
        await motors.retract_tray(steps=3000)
        
        # 3. XY хоминг
        await motors.home_with_sensors()
```

### ⚠️ Известная проблема: retract_tray без концевика

`retract_tray(3000)` двигает лоток назад на **3000 шагов вслепую**, без проверки концевика заднего конца.

**Риск:** если лоток уже в крайнем положении или механически заблокирован — возможно напряжение на ремень/мотор.

**Рекомендация:** добавить проверку SENSOR_TRAY_BEGIN (GPIO 20) перед blind retract.

**Issue:** нужен отдельный issue для исправления.

---

## Известные проблемы при старте

### 1. Шелест замков при старте (исправлено)

**Проблема:** при инициализации GPIO замки получали кратковременный PWM-импульс → слышен щелчок/шелест.

**Статус:** ✅ Исправлено в issue #77.

**Решение:** инициализировать PWM только перед реальным использованием, не при старте.

### 2. Blind retract_tray (не исправлено)

**Проблема:** `StartupRecovery` делает 3000 шагов назад без концевика.

**Статус:** ⚠️ Открытый риск.

**Обходной путь:** перед перезапуском сервиса убедиться что лоток в центральном положении.

### 3. Дребезг SENSOR_TRAY_BEGIN (GPIO 20)

**Проблема:** задний концевик лотка может давать ложные срабатывания.

**Статус:** ⚠️ Нужен software debounce.

**Реализовано:** `sensor_stable()` в `shelf_operations.py` — требует 5 стабильных HIGH.

---

## Логи и мониторинг

### Лог файл

```
/home/admin42/bookcabinet/logs/bookcabinet.log
```

### Просмотр в реальном времени

```bash
tail -f /home/admin42/bookcabinet/logs/bookcabinet.log
# или через journalctl:
journalctl -u bookcabinet -f
```

### Таблица `system_log` в БД

```sql
SELECT * FROM system_log ORDER BY timestamp DESC LIMIT 50;
```

Поля: `id, timestamp, level, message, source`

---

## Watchdog

`WatchdogService` запускается параллельно основному приложению. Каждые 30 секунд проверяет:

- Позицию моторов (motors.get_position())
- Датчики (sensors.read_all())
- RFID ридеры (card_reader, book_reader)
- БД (database connectivity)
- WebSocket сервер

При 3 последовательных ошибках одной подсистемы → вызывается `error_callback`.

В режиме `MOCK_MODE=false` — отправляет `systemd notify` watchdog heartbeat (sd_notify).
