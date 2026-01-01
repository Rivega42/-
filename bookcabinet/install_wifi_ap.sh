#!/bin/bash
#
# BookCabinet - Настройка Wi-Fi точки доступа
# Запуск: sudo bash install_wifi_ap.sh
#

set -e

echo "========================================"
echo "  Настройка Wi-Fi точки доступа"
echo "========================================"

if [ "$EUID" -ne 0 ]; then
    echo "Ошибка: запустите с sudo"
    exit 1
fi

AP_SSID="BookCabinet"
AP_PASS="BookCabinet123"
AP_IP="192.168.4.1"
AP_INTERFACE="wlan0"

echo ""
echo "[1/4] Установка hostapd и dnsmasq..."
apt install -y hostapd dnsmasq

systemctl stop hostapd
systemctl stop dnsmasq

echo ""
echo "[2/4] Настройка статического IP..."

cat >> /etc/dhcpcd.conf << EOF

# BookCabinet Wi-Fi AP
interface $AP_INTERFACE
    static ip_address=$AP_IP/24
    nohook wpa_supplicant
EOF

echo ""
echo "[3/4] Настройка dnsmasq (DHCP)..."

mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig 2>/dev/null || true

cat > /etc/dnsmasq.conf << EOF
interface=$AP_INTERFACE
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
domain=local
address=/bookcabinet.local/$AP_IP
EOF

echo ""
echo "[4/4] Настройка hostapd..."

cat > /etc/hostapd/hostapd.conf << EOF
interface=$AP_INTERFACE
driver=nl80211
ssid=$AP_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$AP_PASS
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

systemctl unmask hostapd
systemctl enable hostapd
systemctl enable dnsmasq

echo ""
echo "========================================"
echo "  Wi-Fi AP НАСТРОЕНА"
echo "========================================"
echo ""
echo "SSID: $AP_SSID"
echo "Пароль: $AP_PASS"
echo "IP адрес: $AP_IP"
echo ""
echo "После перезагрузки подключитесь к сети '$AP_SSID'"
echo "и откройте http://$AP_IP:5000"
echo ""
echo "Перезагрузите: sudo reboot"
echo "========================================"
