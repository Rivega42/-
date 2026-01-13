# test_rru9816_protocol.py
# Тест: понимает ли RRU9816 китайский UHF протокол 0xA0
#
# Запуск: py test_rru9816_protocol.py
# Требуется: py -m pip install pyserial

import serial

PORT = "COM16"

def checksum(data):
    """Китайский UHF checksum: (~SUM + 1) & 0xFF"""
    return (~sum(data) + 1) & 0xFF

def build_cmd(addr, cmd, data=b''):
    """Формат: 0xA0 + len + addr + cmd + data + checksum"""
    length = len(data) + 3  # addr + cmd + checksum
    packet = bytes([0xA0, length, addr, cmd]) + data
    packet += bytes([checksum(packet[1:])])  # checksum без 0xA0
    return packet

# Команда Inventory (типичная для китайских UHF ридеров)
INVENTORY_CMD = build_cmd(0x00, 0x01)

print(f"Порт: {PORT}")
print(f"Отправляем: {INVENTORY_CMD.hex(' ')}")

try:
    ser = serial.Serial(PORT, 57600, timeout=2)
    ser.write(INVENTORY_CMD)
    response = ser.read(64)
    print(f"Ответ: {response.hex(' ') if response else 'нет ответа'}")
    ser.close()
except serial.SerialException as e:
    print(f"Ошибка порта: {e}")
