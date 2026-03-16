#!/usr/bin/env python3
"""
Демон авторизации BookCabinet v2
- lgpio напрямую (без RPi.GPIO wrapper)
- При любой карте: открывает SHUTTER_OUTER (pin 2) на 30 секунд
"""
import sys
sys.path.insert(0, '/home/admin42/.local/lib/python3.13/site-packages')
sys.path.insert(0, '/usr/lib/python3/dist-packages')

import time, json, threading, serial

def emit(data):
    print(json.dumps(data, ensure_ascii=False), flush=True)

# ─── GPIO через lgpio напрямую ─────────────────────────────
try:
    import lgpio
    chip = lgpio.gpiochip_open(0)
    SHUTTER_OUTER = 2
    SHUTTER_INNER = 3
    lgpio.gpio_claim_output(chip, SHUTTER_OUTER, 0)  # LOW = закрыта
    lgpio.gpio_claim_output(chip, SHUTTER_INNER, 0)
    HAS_GPIO = True
    emit({"type": "info", "message": f"GPIO OK: chip={chip}, pins 2,3 claimed"})
except Exception as e:
    HAS_GPIO = False
    chip = None
    emit({"type": "warning", "message": f"GPIO недоступен: {e}"})

# ─── Управление шторкой ───────────────────────────────────
shutter_lock = threading.Lock()
shutter_open_until = 0.0

def open_shutter():
    global shutter_open_until
    with shutter_lock:
        already_open = time.time() < shutter_open_until
        shutter_open_until = time.time() + 30
        if not already_open:
            if HAS_GPIO:
                try:
                    lgpio.gpio_write(chip, SHUTTER_OUTER, 1)
                    emit({"type": "shutter", "state": "open", "seconds": 30})
                except Exception as e:
                    emit({"type": "error", "message": f"GPIO write fail: {e}"})
            else:
                emit({"type": "shutter", "state": "open", "seconds": 30, "gpio": False})

def shutter_watcher():
    global shutter_open_until
    while True:
        time.sleep(0.5)
        with shutter_lock:
            if shutter_open_until > 0 and time.time() >= shutter_open_until:
                shutter_open_until = 0
                if HAS_GPIO:
                    try:
                        lgpio.gpio_write(chip, SHUTTER_OUTER, 0)
                    except Exception as e:
                        emit({"type": "error", "message": f"GPIO close fail: {e}"})
                emit({"type": "shutter", "state": "closed"})

threading.Thread(target=shutter_watcher, daemon=True).start()

# ─── CRC для IQRFID ───────────────────────────────────────
def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
    return bytes([crc & 0xFF, crc >> 8])

pkt = bytes([4, 0x00, 0x01])
CMD_INV = pkt + crc16(pkt)

# ─── UHF поток (IQRFID-5102) ──────────────────────────────
def uhf_worker():
    while True:
        try:
            ser = serial.Serial('/dev/ttyUSB2', 57600, timeout=0.5)
            emit({"type": "info", "reader": "IQRFID-5102", "message": "Подключён"})
            last = set()
            while True:
                ser.reset_input_buffer()
                ser.write(CMD_INV)
                time.sleep(0.15)
                resp = ser.read(256)
                current = set()
                if resp and len(resp) > 6 and resp[3] == 0x01:
                    count = resp[4]
                    off = 5
                    for _ in range(count):
                        if off >= len(resp) - 2: break
                        off += 1
                        epc_len = resp[off]; off += 1
                        if off + epc_len > len(resp) - 2: break
                        epc = resp[off:off+epc_len].hex().upper()
                        off += epc_len
                        if epc:
                            current.add(epc)
                for epc in current - last:
                    emit({"type": "card_detected", "reader": "IQRFID-5102", "uid": epc})
                    open_shutter()
                last = current
                time.sleep(0.15)
        except Exception as e:
            emit({"type": "warning", "reader": "IQRFID-5102", "message": str(e)})
            time.sleep(3)

# ─── NFC поток (ACR1281) ──────────────────────────────────
def nfc_worker():
    while True:
        try:
            from smartcard.System import readers
            rs = readers()
            nfc = [r for r in rs if '00 01' in str(r)]
            if not nfc:
                time.sleep(2)
                continue
            reader = nfc[0]
            emit({"type": "info", "reader": "ACR1281", "message": "Подключён"})
            last_uid = None
            while True:
                uid = None
                try:
                    c = reader.createConnection()
                    c.connect()
                    data, sw1, sw2 = c.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                    c.disconnect()
                    if sw1 == 0x90 and data:
                        uid = ''.join(f'{b:02X}' for b in data)
                except Exception:
                    pass
                if uid and uid != last_uid:
                    last_uid = uid
                    emit({"type": "card_detected", "reader": "ACR1281", "uid": uid})
                    open_shutter()
                elif not uid and last_uid:
                    last_uid = None
                time.sleep(0.2)
        except Exception as e:
            emit({"type": "warning", "reader": "ACR1281", "message": str(e)})
            time.sleep(3)

emit({"type": "started", "message": "Auth shutter daemon v2 запущен"})
threading.Thread(target=uhf_worker, daemon=True).start()
threading.Thread(target=nfc_worker, daemon=True).start()

try:
    while True:
        time.sleep(60)
        emit({"type": "heartbeat"})
except KeyboardInterrupt:
    if HAS_GPIO and chip:
        lgpio.gpio_write(chip, SHUTTER_OUTER, 0)
        lgpio.gpio_write(chip, SHUTTER_INNER, 0)
        lgpio.gpiochip_close(chip)
    emit({"type": "stopped"})
