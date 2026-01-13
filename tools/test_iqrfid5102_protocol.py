# test_iqrfid5102_protocol.py
# Тест IQRFID-5102 с протоколом 0xA0 (стандартный китайский UHF)
#
# Запуск: py tools/test_iqrfid5102_protocol.py COM3
# Требуется: py -m pip install pyserial

import serial
import time
import sys

PORT = "COM3"  # Поменяй на свой порт
BAUDRATES = [115200, 57600, 38400, 9600]

def checksum_0xa0(data):
    """Китайский UHF checksum: (~SUM + 1) & 0xFF"""
    return (~sum(data) + 1) & 0xFF

def build_cmd_0xa0(addr, cmd, data=b''):
    """
    Протокол 0xA0:
    [0xA0] [len] [addr] [cmd] [data...] [checksum]
    len = addr + cmd + data + checksum = len(data) + 3
    checksum = (~SUM + 1) & 0xFF от всех байт после 0xA0
    """
    length = len(data) + 3  # addr + cmd + checksum
    packet = bytes([0xA0, length, addr, cmd]) + data
    cs = checksum_0xa0(packet[1:])  # checksum без 0xA0
    packet += bytes([cs])
    return packet

# Команды для протокола 0xA0
COMMANDS = [
    ("Inventory (0x01)", build_cmd_0xa0(0x00, 0x01)),
    ("Inventory (0x80)", build_cmd_0xa0(0x00, 0x80)),
    ("Inventory (0x80) + Q=4", build_cmd_0xa0(0x00, 0x80, bytes([0x04]))),
    ("GetVersion (0x03)", build_cmd_0xa0(0x00, 0x03)),
    ("GetVersion FF", build_cmd_0xa0(0xFF, 0x03)),
    ("Reset (0x70)", build_cmd_0xa0(0x00, 0x70)),
    ("SetRegion EU (0x07)", build_cmd_0xa0(0x00, 0x07, bytes([0x02]))),  # EU band
]

def test_baudrate(port, baud):
    """Тест одного baudrate"""
    print(f"\n--- Baudrate: {baud} ---")
    try:
        ser = serial.Serial(port, baud, timeout=0.5)
        time.sleep(0.2)
        
        # Очистим буфер
        ser.reset_input_buffer()
        
        # Проверим не шлёт ли ридер что-то сам
        time.sleep(0.3)
        initial = ser.read(64)
        if initial:
            print(f"  [!] Ридер сам прислал: {initial.hex(' ')}")
        
        for name, cmd in COMMANDS:
            ser.reset_input_buffer()
            ser.write(cmd)
            time.sleep(0.15)
            response = ser.read(64)
            
            cmd_hex = cmd.hex(' ')
            if response:
                resp_hex = response.hex(' ')
                print(f"  {name}")
                print(f"    TX: {cmd_hex}")
                print(f"    RX: {resp_hex}")
                print(f"    [+] ОТВЕТ ПОЛУЧЕН!")
            else:
                print(f"  {name}: {cmd_hex} -> нет ответа")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"  Ошибка: {e}")

def main():
    global PORT
    
    if len(sys.argv) > 1:
        PORT = sys.argv[1]
    
    print(f"=== Тест IQRFID-5102 на {PORT} ===")
    print(f"Протокол: 0xA0 (стандартный китайский UHF)")
    print(f"Checksum: (~SUM + 1) & 0xFF")
    
    for baud in BAUDRATES:
        test_baudrate(PORT, baud)
    
    print("\n=== Тест завершён ===")
    print("\nЕсли ни один baudrate не дал ответа:")
    print("  1. Проверь питание ридера (нужен внешний БП)")
    print("  2. Проверь что TX/RX не перепутаны")
    print("  3. Попробуй другой USB-TTL адаптер")

if __name__ == "__main__":
    main()
