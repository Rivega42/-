# Disaster Recovery — аварийное восстановление

Документ для библиотекаря и администратора на случай сбоев BookCabinet.

## Быстрые команды

```bash
# Перезапустить UI
sudo systemctl restart bookcabinet-ui

# Посмотреть последние логи
sudo journalctl -u bookcabinet-ui -n 50

# Статус всех сервисов шкафа
sudo systemctl status bookcabinet-daemon bookcabinet-ui bookcabinet-calibration chromium-kiosk

# Полная перекалибровка
python3 /home/admin42/bookcabinet/tools/startup_calibration.py

# Экстренный стоп всей механики
curl -X POST http://localhost:5000/api/emergency-stop
```

---

## Сценарии

### 1. UI не открывается / белый экран

**Симптом:** На мониторе пустой/белый экран после ребута, или "Не удалось подключиться" в Chromium.

**Диагностика:**
```bash
curl http://localhost:5000/api/health
# Ожидаем 200 OK с JSON

sudo systemctl status bookcabinet-ui
sudo journalctl -u bookcabinet-ui -n 30
```

**Починка:**
```bash
sudo systemctl restart bookcabinet-ui
# Если не помогло — проверить что Node.js собран:
cd /home/admin42/bookcabinet
sudo -u admin42 npm run build
sudo systemctl restart bookcabinet-ui
```

**Когда эскалировать:** если после 2 рестартов всё ещё не работает — связаться с разработчиком.

---

### 2. Каретка застряла посреди движения

**Симптом:** Шкаф "замер" во время выдачи, каретка в неизвестной позиции.

**Починка (немедленная):**
1. Нажать **СТОП** на экране (красная кнопка)
2. Или через терминал:
   ```bash
   curl -X POST http://localhost:5000/api/emergency-stop
   ```
3. Подождать 5 секунд
4. Запустить хоминг:
   ```bash
   python3 /home/admin42/bookcabinet/tools/startup_calibration.py
   ```

**Если каретка физически заклинила:**
1. Обесточить шкаф (отключить питание моторов)
2. Вручную сдвинуть каретку к LEFT+BOTTOM (слегка)
3. Включить питание
4. Запустить хоминг

---

### 3. Книга застряла в закрытой ячейке

**Симптом:** Замок не открылся при возврате, книга на лотке, но шторки закрыты.

**Починка:**
```bash
# Экстренная разблокировка обоих замков
python3 -c "
import pigpio, time
pi = pigpio.pi()
pi.set_servo_pulsewidth(12, 500)  # front lock open
pi.set_servo_pulsewidth(13, 500)  # rear lock open
time.sleep(0.5)
pi.set_servo_pulsewidth(12, 0)
pi.set_servo_pulsewidth(13, 0)
pi.stop()
print('Замки разблокированы')
"

# Открыть внешнюю шторку
python3 -c "
import pigpio
pi = pigpio.pi()
pi.set_mode(2, pigpio.OUTPUT)
pi.write(2, 1)  # HIGH = open
pi.stop()
print('Внешняя шторка открыта')
"
```

Достать книгу вручную. После — закрыть всё:
```bash
curl -X POST http://localhost:5000/api/shutters/outer/close
curl -X POST http://localhost:5000/api/shutters/inner/close
```

---

### 4. Шторка не закрывается

**Симптом:** После операции внешняя/внутренняя шторка остаётся открытой.

**Починка:**
```bash
# Принудительно закрыть обе
python3 -c "
import pigpio
pi = pigpio.pi()
pi.set_mode(2, pigpio.OUTPUT)
pi.set_mode(3, pigpio.OUTPUT)
pi.write(2, 0)  # outer close
pi.write(3, 0)  # inner close
pi.stop()
"
```

Если реле не реагирует — проверить физически (клик?). При глюке — перезагрузить RPi:
```bash
sudo reboot
```

При старте стартовая калибровка закроет всё автоматически.

---

### 5. RFID ридеры не детектируют карты

**Симптом:** Читатель прикладывает карту — ничего не происходит на экране.

**Диагностика:**
```bash
# Проверить статус ридеров
curl http://localhost:5000/api/rfid-readers | jq

# Проверить pcscd для NFC
systemctl status pcscd

# USB устройства
lsusb | grep -iE "acr|iqrfid|rru"

# Serial порты
ls /dev/ttyUSB*

# Демон шторок работает?
sudo systemctl status bookcabinet-daemon
sudo journalctl -u bookcabinet-daemon -n 20
```

**Починка:**
```bash
# Перезапустить всё
sudo systemctl restart pcscd
sudo systemctl restart bookcabinet-daemon
```

**Если не помогло:**
- Переподключить USB ридер физически
- Проверить udev правила: `cat /etc/udev/rules.d/99-bookcabinet.rules`
- Перезагрузить udev: `sudo udevadm control --reload-rules && sudo udevadm trigger`

---

### 6. ИРБИС недоступен (нет связи с библиотечной сетью)

**Симптом:** В UI "ИРБИС offline", авторизация работает только по локальным картам.

**Диагностика:**
```bash
# Проверить сеть
ping -c 3 172.29.67.70

# Проверить порт ИРБИС (6666)
nc -zv 172.29.67.70 6666

# Тестовый запрос из Python
python3 -c "
import socket
s = socket.socket()
s.settimeout(3)
try:
    s.connect(('172.29.67.70', 6666))
    print('IRBIS: OK')
except Exception as e:
    print(f'IRBIS: {e}')
s.close()
"
```

**Автономный режим:**
Шкаф продолжает работать без ИРБИС — операции сохраняются в локальную очередь и синхронизируются при восстановлении связи (см. `bookcabinet/irbis/sync_queue.py`).

**Проверить очередь:**
```bash
cat /home/admin42/bookcabinet/data/irbis_queue.json
```

**Форсировать синхронизацию:**
```bash
curl -X POST http://localhost:5000/api/irbis/sync
```

---

### 7. SD карта повреждена

**Симптом:** RPi не загружается, ошибки ФС в dmesg.

**Восстановление из бэкапа:**
1. Записать чистый образ Raspberry Pi OS на новую SD:
   ```bash
   sudo dd if=raspios-bookworm-arm64.img of=/dev/sdX bs=4M status=progress
   ```
2. Загрузиться с новой карты, подключиться по SSH
3. Клонировать репозиторий:
   ```bash
   git clone https://github.com/Rivega42/-.git bookcabinet
   cd bookcabinet
   ```
4. Восстановить БД из последнего бэкапа:
   ```bash
   # Бэкапы в /home/admin42/bookcabinet/backups/
   cp backups/2026-XX-XX/shelf_data.db data/
   cp backups/2026-XX-XX/calibration.json .
   ```
5. Установить сервисы:
   ```bash
   sudo bash deploy/install.sh
   sudo reboot
   ```

**Профилактика:**
- Настроить регулярное резервное копирование (Settings → Backup → auto, interval 24h)
- Хранить резервные копии на внешнем диске/облаке

---

### 8. Калибровка сбилась (ячейки не совпадают с полками)

**Симптом:** Каретка приезжает мимо полки на 1-2 см, не может захватить.

**Быстрый фикс:**
```bash
# Проверить текущую калибровку
cat /home/admin42/bookcabinet/calibration.json | jq

# Запустить калибровку стоек в UI:
# Admin → Калибровка → "Тест" возле каждой стойки
```

**Полная перекалибровка:**
1. Admin → Калибровка → 10-точечная калибровка (wizard)
2. Или вручную: через Teach Mode записать правильные позиции

**Важно:** После калибровки сохранить бэкап `calibration.json`.

---

### 9. pigpiod упал / не запускается

**Симптом:** В логах `pigpio.error: connection refused`, вся механика не работает.

**Починка:**
```bash
sudo systemctl status pigpiod
sudo systemctl restart pigpiod

# Если не помогло — вручную
sudo killall pigpiod
sudo pigpiod -l

# Проверить
pigs t
```

Если pigpiod отказывается стартовать — скорее всего другой процесс уже держит GPIO (`RPi.GPIO`, `gpiozero`). Убить всех:
```bash
sudo pkill -f "python.*gpio"
sudo systemctl restart pigpiod
```

---

### 10. Температура >85°C / перегрев

**Симптом:** Watchdog шлёт алерт в Telegram, шкаф работает с замедлениями.

**Диагностика:**
```bash
vcgencmd measure_temp
cat /sys/class/thermal/thermal_zone0/temp
```

**Починка:**
- Проверить кулер/радиатор на RPi
- Проверить вентиляцию шкафа (нет ли закрытых вентотверстий)
- Летом может потребоваться активный кулер с PWM

**Временное решение:** замедлить моторы чтобы снизить нагрузку:
```bash
# В Settings → уменьшить скорости XY до 500
```

---

## Контакты эскалации

Заполнить при развёртывании:
- **Администратор:** _____ (телефон)
- **Разработчик:** _____ (Telegram, email)
- **Telegram бот для alerts:** настраивается в Settings Panel
- **GitHub Issues:** https://github.com/Rivega42/-/issues

## Логи для репортов

При создании GitHub issue прикладывать:
```bash
# Соберёт последние 200 строк каждого сервиса
for svc in bookcabinet-daemon bookcabinet-ui pigpiod; do
    echo "=== $svc ===" >> diagnostic.log
    sudo journalctl -u $svc -n 200 --no-pager >> diagnostic.log
done

# Состояние железа
echo "=== hardware ===" >> diagnostic.log
pigs t >> diagnostic.log
lsusb >> diagnostic.log
ls /dev/ttyUSB* >> diagnostic.log
vcgencmd measure_temp >> diagnostic.log
df -h >> diagnostic.log
```
