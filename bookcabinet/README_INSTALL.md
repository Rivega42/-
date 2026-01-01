# Развёртывание BookCabinet на Raspberry Pi 4

## Требования

- Raspberry Pi 4 (2GB+ RAM)
- Raspberry Pi OS (Bookworm или Bullseye)
- MicroSD 16GB+
- Сенсорный экран 1920×1080
- ACR1281U-C1 NFC ридер (USB)
- IQRFID-5102 UHF ридер (Serial)

## Быстрая установка

### 1. Подготовка SD карты

Установите Raspberry Pi OS с помощью Raspberry Pi Imager.

### 2. Копирование файлов

```bash
# С вашего компьютера
scp -r bookcabinet pi@raspberrypi.local:~/
```

### 3. Установка

```bash
# На Raspberry Pi
cd ~/bookcabinet
sudo bash install_raspberry.sh
```

### 4. Копирование кода

```bash
# Убедитесь что все файлы на месте
ls -la ~/bookcabinet/
```

### 5. Перезагрузка

```bash
sudo reboot
```

## Проверка работы

```bash
# Статус сервиса
sudo systemctl status bookcabinet

# Логи
journalctl -u bookcabinet -f

# Проверка pigpio
pigs t  # должен вернуть число (uptime в мс)

# Проверка RFID карт
pcsc_scan  # покажет подключённые ридеры
```

## Wi-Fi точка доступа (опционально)

Если нужен автономный режим без роутера:

```bash
sudo bash install_wifi_ap.sh
sudo reboot
```

Подключитесь к сети `BookCabinet` (пароль: `BookCabinet123`)
Откройте http://192.168.4.1:5000

## Подключение оборудования

### GPIO пины

| Функция | GPIO |
|---------|------|
| Motor A STEP | 18 |
| Motor A DIR | 27 |
| Motor B STEP | 23 |
| Motor B DIR | 22 |
| Tray STEP | 24 |
| Tray DIR | 25 |
| Servo Lock 1 | 12 |
| Servo Lock 2 | 13 |
| Shutter Outer | 4 |
| Shutter Inner | 5 |
| Sensor X Begin | 16 |
| Sensor X End | 20 |
| Sensor Y Begin | 21 |
| Sensor Y End | 26 |
| Sensor Tray Begin | 19 |
| Sensor Tray End | 6 |

### RFID ридеры

- **ACR1281U-C1**: подключить к USB, определится как PC/SC
- **IQRFID-5102**: подключить к /dev/ttyUSB0 (или /dev/serial0)

## Устранение неполадок

### pigpio не работает
```bash
sudo systemctl restart pigpiod
sudo systemctl status pigpiod
```

### RFID карты не читаются
```bash
sudo systemctl restart pcscd
pcsc_scan
```

### Сервис не запускается
```bash
journalctl -u bookcabinet -n 50
```

### Проверка портов
```bash
ls -la /dev/ttyUSB*
ls -la /dev/serial*
```
