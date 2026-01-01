#!/bin/bash
#
# BookCabinet - Скрипт развёртывания на Raspberry Pi 4
# Запуск: sudo bash install_raspberry.sh
#

set -e

echo "========================================"
echo "  BookCabinet - Установка на Raspberry Pi"
echo "========================================"

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo "Ошибка: запустите с sudo"
    exit 1
fi

# Проверка Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Предупреждение: это не Raspberry Pi"
    read -p "Продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

INSTALL_DIR="/home/pi/bookcabinet"
SERVICE_USER="pi"

echo ""
echo "[1/7] Обновление системы..."
apt update
apt upgrade -y

echo ""
echo "[2/7] Установка системных зависимостей..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    pigpio \
    python3-pigpio \
    pcscd \
    pcsc-tools \
    libpcsclite-dev \
    swig \
    git

echo ""
echo "[3/7] Настройка pigpio демона..."
systemctl enable pigpiod
systemctl start pigpiod

echo ""
echo "[4/7] Создание виртуального окружения..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

python3 -m venv venv
source venv/bin/activate

echo ""
echo "[5/7] Установка Python зависимостей..."
pip install --upgrade pip
pip install \
    aiohttp \
    pyscard \
    pyserial

echo ""
echo "[6/7] Настройка прав доступа..."
# Права на serial порт для RFID
usermod -a -G dialout $SERVICE_USER
usermod -a -G gpio $SERVICE_USER

# Права на директорию
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

echo ""
echo "[7/7] Создание systemd сервиса..."

cat > /etc/systemd/system/bookcabinet.service << 'EOF'
[Unit]
Description=BookCabinet Library RFID Kiosk
After=network.target pigpiod.service pcscd.service
Requires=pigpiod.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/bookcabinet
ExecStart=/home/pi/bookcabinet/venv/bin/python3 main.py
Restart=always
RestartSec=5
Environment=MOCK_MODE=false
Environment=HOST=0.0.0.0
Environment=PORT=5000
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bookcabinet

echo ""
echo "========================================"
echo "  УСТАНОВКА ЗАВЕРШЕНА"
echo "========================================"
echo ""
echo "Следующие шаги:"
echo ""
echo "1. Скопируйте файлы проекта в $INSTALL_DIR"
echo "   scp -r bookcabinet/* pi@<IP>:$INSTALL_DIR/"
echo ""
echo "2. Перезагрузите Raspberry Pi"
echo "   sudo reboot"
echo ""
echo "3. Проверьте статус сервиса"
echo "   sudo systemctl status bookcabinet"
echo ""
echo "4. Смотрите логи"
echo "   journalctl -u bookcabinet -f"
echo ""
echo "5. Веб-интерфейс доступен по адресу:"
echo "   http://<IP>:5000"
echo ""
echo "========================================"
