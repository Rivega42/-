#!/bin/bash
#
# Установка udev правил для стабильного именования RFID устройств
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  BookCabinet - Установка udev правил"
echo "========================================"
echo ""

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Ошибка: запустите с sudo${NC}"
    echo "  sudo bash setup_udev_rules.sh"
    exit 1
fi

# Путь к файлу правил
RULES_FILE="udev/99-bookcabinet-rfid.rules"
DEST_FILE="/etc/udev/rules.d/99-bookcabinet-rfid.rules"

# Проверка существования файла правил
if [ ! -f "$RULES_FILE" ]; then
    echo -e "${RED}Ошибка: файл $RULES_FILE не найден${NC}"
    echo "  Убедитесь, что вы находитесь в директории bookcabinet/"
    exit 1
fi

echo "Устанавливаем udev правила..."

# Копируем файл правил
cp "$RULES_FILE" "$DEST_FILE"
chmod 644 "$DEST_FILE"
echo -e "${GREEN}✓ Правила скопированы в $DEST_FILE${NC}"

# Перезагружаем правила
echo "Применяем правила..."
udevadm control --reload-rules
udevadm trigger
echo -e "${GREEN}✓ Правила применены${NC}"

# Ждём немного для создания симлинков
sleep 2

echo ""
echo "Проверка символических ссылок:"
echo "-------------------------------"

# Проверяем создались ли симлинки
if [ -L /dev/rfid_uhf_card ]; then
    REAL_PATH=$(readlink -f /dev/rfid_uhf_card)
    echo -e "${GREEN}✓ /dev/rfid_uhf_card → $REAL_PATH${NC}"
else
    echo -e "${YELLOW}⚠ /dev/rfid_uhf_card не создан${NC}"
    echo "  Возможно, IQRFID-5102 не подключен или на другом порту"
fi

if [ -L /dev/rfid_book ]; then
    REAL_PATH=$(readlink -f /dev/rfid_book)
    echo -e "${GREEN}✓ /dev/rfid_book → $REAL_PATH${NC}"
else
    echo -e "${YELLOW}⚠ /dev/rfid_book не создан${NC}"
    echo "  Возможно, RRU9816 не подключен или на другом порту"
fi

echo ""
echo "Текущие USB-Serial устройства:"
echo "------------------------------"
ls -la /dev/ttyUSB* 2>/dev/null || echo "Нет USB-Serial устройств"

echo ""
echo "Информация о подключенных устройствах:"
echo "--------------------------------------"
for dev in /dev/ttyUSB*; do
    if [ -e "$dev" ]; then
        echo "$dev:"
        udevadm info --query=property --name="$dev" | grep -E "ID_VENDOR|ID_MODEL|DEVPATH" | head -3
        echo ""
    fi
done

echo ""
echo "========================================"
echo -e "${GREEN}  УСТАНОВКА ЗАВЕРШЕНА${NC}"
echo "========================================"
echo ""
echo "Что делать дальше:"
echo ""
echo "1. Если символические ссылки не создались:"
echo "   - Проверьте подключение устройств"
echo "   - Проверьте USB порты (должны совпадать с DEVPATH в правилах)"
echo "   - Отредактируйте $DEST_FILE при необходимости"
echo ""
echo "2. Перезапустите сервис BookCabinet:"
echo "   sudo systemctl restart bookcabinet"
echo ""
echo "3. Проверьте логи:"
echo "   sudo journalctl -u bookcabinet -f"
echo ""
