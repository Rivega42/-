#!/bin/bash
#
# BookCabinet - Скрипт развёртывания на Raspberry Pi
# Версия: 2.1 (Bookworm/Trixie compatible)
# Запуск: sudo bash install_raspberry.sh
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  BookCabinet - Установка на Raspberry Pi"
echo "  Версия 2.1"
echo "========================================"
echo ""

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: запустите с sudo${NC}"
    exit 1
fi

# Проверка Raspberry Pi
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${GREEN}✓ Обнаружен Raspberry Pi${NC}"
    RPI_MODEL=$(cat /proc/cpuinfo | grep 'Model' | cut -d ':' -f2 | xargs)
    echo "  Модель: $RPI_MODEL"
else
    echo -e "${YELLOW}⚠ Это не Raspberry Pi${NC}"
    read -p "Продолжить установку? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Определяем текущего пользователя (того кто вызвал sudo)
SERVICE_USER=${SUDO_USER:-pi}
INSTALL_DIR="/home/$SERVICE_USER/bookcabinet/bookcabinet"
LOG_FILE="/var/log/bookcabinet_install.log"

echo "  Пользователь: $SERVICE_USER"
echo "  Директория: $INSTALL_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo -e "${YELLOW}[1/9] Обновление системы...${NC}"
apt update
apt upgrade -y

echo ""
echo -e "${YELLOW}[2/9] Установка системных зависимостей...${NC}"
# Примечание: pigpio и python3-pigpio устанавливаются вручную из исходников
# если пакет недоступен в репозитории (Trixie)
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-aiohttp \
    python3-serial \
    pcscd \
    pcsc-tools \
    libpcsclite-dev \
    libpcsclite1 \
    swig \
    git \
    sqlite3 \
    libi2c-dev \
    i2c-tools \
    chromium \
    unclutter || echo -e "${YELLOW}Некоторые пакеты не установились, продолжаем...${NC}"

echo ""
echo -e "${YELLOW}[3/9] Настройка pigpio демона...${NC}"
# Проверяем установлен ли pigpio
if command -v pigpiod &> /dev/null; then
    echo -e "${GREEN}✓ pigpiod найден${NC}"
    
    # Создаём systemd сервис если его нет
    if [ ! -f /etc/systemd/system/pigpiod.service ]; then
        cat > /etc/systemd/system/pigpiod.service << 'EOF'
[Unit]
Description=Pigpio daemon
After=network.target

[Service]
ExecStart=/usr/local/bin/pigpiod -l
ExecStop=/bin/systemctl kill pigpiod
Type=forking

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
    fi
    
    systemctl enable pigpiod
    systemctl start pigpiod || true
else
    echo -e "${YELLOW}⚠ pigpiod не найден. Установите вручную из исходников:${NC}"
    echo "  wget https://github.com/joan2937/pigpio/archive/master.zip"
    echo "  unzip master.zip && cd pigpio-master && make && sudo make install"
fi

# Проверка pigpio
if pigs t > /dev/null 2>&1; then
    echo -e "${GREEN}✓ pigpiod работает${NC}"
else
    echo -e "${YELLOW}⚠ pigpiod не запустился${NC}"
fi

echo ""
echo -e "${YELLOW}[4/9] Настройка PC/SC демона (RFID карты)...${NC}"
systemctl stop pcscd 2>/dev/null || true
systemctl enable pcscd
systemctl start pcscd

# Проверка pcscd
if systemctl is-active --quiet pcscd; then
    echo -e "${GREEN}✓ pcscd работает${NC}"
else
    echo -e "${YELLOW}⚠ pcscd не запустился (нормально без ридера)${NC}"
fi

echo ""
echo -e "${YELLOW}[5/9] Настройка serial портов...${NC}"
# Определяем путь к config.txt (разный в разных версиях ОС)
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_TXT="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_TXT="/boot/config.txt"
else
    CONFIG_TXT=""
fi

if [ -n "$CONFIG_TXT" ]; then
    if ! grep -q "enable_uart=1" "$CONFIG_TXT" 2>/dev/null; then
        echo "enable_uart=1" >> "$CONFIG_TXT"
        echo -e "${GREEN}✓ UART включён в config.txt${NC}"
    else
        echo -e "${GREEN}✓ UART уже включён${NC}"
    fi
fi

# Отключить serial console
if [ -f /boot/cmdline.txt ]; then
    sed -i 's/console=serial0,115200 //g' /boot/cmdline.txt 2>/dev/null || true
fi
if [ -f /boot/firmware/cmdline.txt ]; then
    sed -i 's/console=serial0,115200 //g' /boot/firmware/cmdline.txt 2>/dev/null || true
fi

echo ""
echo -e "${YELLOW}[6/9] Настройка директорий...${NC}"
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/backups

echo ""
echo -e "${YELLOW}[7/9] Установка Python зависимостей...${NC}"
# В Bookworm+ используем --break-system-packages для системного Python
pip3 install --break-system-packages pyscard 2>/dev/null || \
    pip3 install pyscard 2>/dev/null || \
    echo -e "${YELLOW}⚠ pyscard уже установлен или требует ручной установки${NC}"

echo ""
echo -e "${YELLOW}[8/9] Настройка прав доступа...${NC}"

# Группы для пользователя
usermod -a -G dialout $SERVICE_USER 2>/dev/null || true
usermod -a -G gpio $SERVICE_USER 2>/dev/null || true
usermod -a -G i2c $SERVICE_USER 2>/dev/null || true
usermod -a -G spi $SERVICE_USER 2>/dev/null || true
usermod -a -G plugdev $SERVICE_USER 2>/dev/null || true

# udev правило для RFID ридеров
cat > /etc/udev/rules.d/99-bookcabinet.rules << 'EOF'
# ACR1281U-C1 NFC Reader
SUBSYSTEM=="usb", ATTR{idVendor}=="072f", ATTR{idProduct}=="2200", MODE="0666", GROUP="plugdev"

# Generic USB Serial
SUBSYSTEM=="tty", ATTRS{idVendor}=="*", MODE="0666", GROUP="dialout"
EOF

udevadm control --reload-rules
udevadm trigger

# Права на директорию
chown -R $SERVICE_USER:$SERVICE_USER /home/$SERVICE_USER/bookcabinet

echo ""
echo -e "${YELLOW}[9/9] Создание systemd сервисов...${NC}"

# Основной сервис
cat > /etc/systemd/system/bookcabinet.service << EOF
[Unit]
Description=BookCabinet Library RFID Kiosk
After=network.target pigpiod.service pcscd.service
Wants=pigpiod.service pcscd.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
Environment=MOCK_MODE=false
Environment=HOST=0.0.0.0
Environment=PORT=5000
StandardOutput=journal
StandardError=journal

# Watchdog
WatchdogSec=60
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

# Сервис автобэкапа
cat > /etc/systemd/system/bookcabinet-backup.service << EOF
[Unit]
Description=BookCabinet Backup Service
After=bookcabinet.service

[Service]
Type=oneshot
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 -c "from bookcabinet.monitoring.backup import backup_manager; backup_manager.create_backup('scheduled')"
EOF

cat > /etc/systemd/system/bookcabinet-backup.timer << 'EOF'
[Unit]
Description=BookCabinet Daily Backup Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable bookcabinet
systemctl enable bookcabinet-backup.timer

# Создать дефолтный calibration.json v2.1
if [ ! -f $INSTALL_DIR/calibration.json ]; then
cat > $INSTALL_DIR/calibration.json << 'EOF'
{
  "version": "2.1",
  "timestamp": "",
  "kinematics": {
    "x_plus_dir_a": 1,
    "x_plus_dir_b": -1,
    "y_plus_dir_a": 1,
    "y_plus_dir_b": 1
  },
  "positions": {
    "x": [1891, 6392, 10894],
    "y": [0, 423, 846, 1269, 1692, 2115, 2538, 2961, 3384, 3807, 4230, 4653, 5076, 5499, 5922, 6345, 6768, 7191, 7614, 8037, 8460]
  },
  "speeds": {
    "xy": 4000,
    "tray": 2000,
    "acceleration": 8000
  },
  "servos": {
    "lock1_open": 0,
    "lock1_close": 95,
    "lock2_open": 0,
    "lock2_close": 95
  },
  "grab_front": {
    "extend1": 1900,
    "retract": 1500,
    "extend2": 3100
  },
  "grab_back": {
    "extend1": 1900,
    "retract": 1500,
    "extend2": 3100
  },
  "tray": {
    "extend_steps": 5000,
    "retract_steps": 5000
  },
  "blocked_cells": {
    "front": {
      "1": [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    },
    "back": {
      "0": [19, 20],
      "1": [19, 20],
      "2": [20]
    }
  }
}
EOF
chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/calibration.json
echo -e "${GREEN}✓ calibration.json создан${NC}"
else
echo -e "${GREEN}✓ calibration.json уже существует${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}  УСТАНОВКА ЗАВЕРШЕНА${NC}"
echo "========================================"
echo ""
echo "Проверка оборудования:"
echo "----------------------"

# Проверка GPIO
if pigs t > /dev/null 2>&1; then
    PIGPIO_TIME=$(pigs t)
    echo -e "${GREEN}✓ GPIO (pigpio): работает (uptime: ${PIGPIO_TIME}мс)${NC}"
else
    echo -e "${RED}✗ GPIO (pigpio): не работает${NC}"
fi

# Проверка PC/SC
if systemctl is-active --quiet pcscd; then
    echo -e "${GREEN}✓ PC/SC демон: работает${NC}"
else
    echo -e "${YELLOW}⚠ PC/SC демон: не работает${NC}"
fi

# Проверка Serial
if ls /dev/ttyUSB* 2>/dev/null || ls /dev/ttyAMA* 2>/dev/null; then
    echo -e "${GREEN}✓ Serial порты: доступны${NC}"
    ls /dev/ttyUSB* /dev/ttyAMA* 2>/dev/null | head -3
else
    echo -e "${YELLOW}⚠ Serial порты: не найдены (подключите RFID ридер)${NC}"
fi

# Проверка I2C
if i2cdetect -y 1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ I2C: доступен${NC}"
else
    echo -e "${YELLOW}⚠ I2C: не настроен (raspi-config -> Interfaces)${NC}"
fi

echo ""
echo "Следующие шаги:"
echo "---------------"
echo "1. Перезагрузите Raspberry Pi:"
echo "   sudo reboot"
echo ""
echo "2. Проверьте статус сервиса:"
echo "   sudo systemctl status bookcabinet"
echo ""
echo "3. Смотрите логи:"
echo "   journalctl -u bookcabinet -f"
echo ""
echo "4. Веб-интерфейс:"
echo "   http://<IP>:5000"
echo ""
echo "Лог установки: $LOG_FILE"
echo "========================================"
