# BookCabinet — RFID Считыватели

## Обзор

| Порт | Устройство | Назначение | Baudrate | Драйвер |
|------|------------|------------|----------|---------|
| /dev/ttyUSB0 (обычно) | **RRU9816** | UHF книги | 57600 | `bookcabinet/hardware/rru9816_driver.py` |
| /dev/ttyUSB1 (обычно) | **IQRFID-5102** | UHF карты ЕКП | 57600 | `bookcabinet/rfid/unified_card_reader.py` |
| PC/SC | **ACR1281 1S Dual Reader** | NFC читательские билеты | - | pyscard |

**ВАЖНО:** Порты могут меняться при переподключении USB! Используй udev rules для фиксации.

---

## RRU9816 (UHF книги)

### Характеристики
- Частота: 865-868 МГц (EU) / 902-928 МГц (US)
- Протокол меток: ISO 18000-6C (EPC Gen2)
- Дальность: до 1м
- Baudrate: 57600 (по умолчанию)

### Драйвер
```
bookcabinet/hardware/rru9816_driver.py
```

### Использование
```python
from bookcabinet.hardware.rru9816_driver import RRU9816

reader = RRU9816('/dev/ttyUSB0', baudrate=57600)
if reader.connect():
    tags = reader.inventory_continuous(2.0)  # сканировать 2 сек
    for tag in tags:
        print(f'EPC: {tag}')
    reader.disconnect()
```

### Тест
```bash
python3 bookcabinet/hardware/rru9816_driver.py /dev/ttyUSB0
```

### Протокол
- Frame: [Len][Addr][Cmd][Data...][CRC16-L][CRC16-H]
- Get Info: `04 ff 21 19 95`
- Inventory: `09 00 01 01 00 00 80 0a 76 fc`
- Response OK: status byte = 0x01, count > 0

---

## IQRFID-5102 (UHF карты ЕКП)

### Характеристики
- Частота: 865-868 МГц
- Протокол меток: ISO 18000-6C
- Дальность: ~20 см (оптимизировано для карт)
- Baudrate: 57600

### Драйвер
```
bookcabinet/rfid/unified_card_reader.py (класс UHFCardReader)
bookcabinet/rfid/book_reader.py (старый, для справки)
```

### Использование
```python
from bookcabinet.rfid.unified_card_reader import unified_reader

unified_reader.configure(uhf_port='/dev/ttyUSB1')
status = await unified_reader.connect()
unified_reader.on_card_read = lambda uid, source: print(f'{source}: {uid}')
await unified_reader.start(poll_interval=0.3)
```

### Протокол
- Frame: [Len][Addr][Cmd][Data...][CRC16-L][CRC16-H]
- CRC: CRC-16/CCITT-FALSE (poly 0x8408)
- Inventory CMD: 0x01

---

## ACR1281 1S Dual Reader (NFC)

### Характеристики
- Частота: 13.56 МГц
- Протоколы: ISO 14443 A/B, Mifare, FeliCa
- Интерфейс: USB (PC/SC)
- 3 виртуальных слота в PC/SC

### Драйвер
```
bookcabinet/rfid/card_reader.py (через pyscard)
bookcabinet/rfid/unified_card_reader.py (класс NFCReader)
```

### Зависимости
```bash
sudo apt install pcscd pcsc-tools
pip install pyscard
```

### Проверка подключения
```bash
pcsc_scan -r
```

### Использование
```python
from bookcabinet.rfid.unified_card_reader import unified_reader

status = await unified_reader.connect()  # автоматически найдёт ACR1281
unified_reader.on_card_read = lambda uid, source: print(f'{source}: {uid}')
await unified_reader.start()
```

---

## Конфигурация

Порты настраиваются в `bookcabinet/config.py`:

```python
RFID = {
    'book_reader': '/dev/ttyUSB0',        # RRU9816
    'book_baudrate': 57600,
    'uhf_card_reader': '/dev/ttyUSB1',    # IQRFID-5102
    'uhf_card_baudrate': 57600,
    'card_poll_interval': 0.3,
}
```

---

## udev Rules (фиксация портов)

Создать `/etc/udev/rules.d/99-bookcabinet-rfid.rules`:

```
# RRU9816 (книги) - первый CP210x
SUBSYSTEM==tty, ATTRS{idVendor}==10c4, ATTRS{idProduct}==ea60, SYMLINK+=rfid_books, MODE=0666

# IQRFID-5102 (карты) - второй CP210x  
# Нужно различать по serial number если есть
```

После изменений:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

## Файлы

| Файл | Назначение |
|------|------------|
| `bookcabinet/hardware/rru9816_driver.py` | Драйвер RRU9816 |
| `bookcabinet/rfid/book_reader.py` | Старый драйвер UHF (IQRFID протокол) |
| `bookcabinet/rfid/card_reader.py` | NFC через PC/SC |
| `bookcabinet/rfid/unified_card_reader.py` | Unified: NFC + UHF карты |
| `bookcabinet/config.py` | Настройки портов |
| `tools/test_rru9816_protocol.py` | Тест RRU9816 |
| `tools/serial_sniffer.py` | Сниффер для реверса протокола |

---

## Troubleshooting

### Порт занят
```bash
lsof /dev/ttyUSB0
# или
fuser /dev/ttyUSB0
```

### Нет ответа от считывателя
1. Проверь baudrate (57600 или 115200)
2. Проверь что сервис bookcabinet не занял порт
3. Попробуй другой ttyUSB

### PC/SC не видит ACR1281
```bash
sudo systemctl restart pcscd
pcsc_scan -r
```

---

## Проверено 14.04.2026

Все три считывателя работают через сервис bookcabinet:

| Считыватель | Назначение | Тестовый UID | Статус |
|-------------|------------|--------------|--------|
| ACR1281 (NFC) | Библиотечная карта | `04239092F17380` | ✅ |
| IQRFID-5102 (UHF) | Карта ЕКП | `304DB75F19600021F0138249` | ✅ |
| RRU9816 (UHF) | Книги | `304DB75F196000090008761B` | ✅ |

### Текущие порты (после перезагрузки могут измениться!)
- /dev/ttyUSB1 — IQRFID-5102 (карты ЕКП)
- /dev/ttyUSB2 — RRU9816 (книги)
- PC/SC — ACR1281 (NFC библиотечные карты)
