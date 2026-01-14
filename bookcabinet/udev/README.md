# Udev правила для RFID устройств BookCabinet

## Назначение

Эти правила создают стабильные символические ссылки для RFID считывателей, чтобы они всегда имели одинаковые имена устройств независимо от порядка подключения.

## Устройства

| Устройство | Модель | Порт по умолчанию | Символическая ссылка | Назначение |
|------------|--------|-------------------|---------------------|------------|
| UHF карты | IQRFID-5102 | /dev/ttyUSB0 | /dev/rfid_uhf_card | Чтение ЕКП карт |
| UHF книги | RRU9816 | /dev/ttyUSB1 | /dev/rfid_book | Чтение книжных меток |
| NFC карты | ACR1281U-C | PC/SC | - | Читательские билеты |

## Установка

### Автоматическая установка

```bash
cd ~/bookcabinet/bookcabinet
sudo bash setup_udev_rules.sh
```

### Ручная установка

```bash
# Копируем правила
sudo cp udev/99-bookcabinet-rfid.rules /etc/udev/rules.d/

# Применяем правила
sudo udevadm control --reload-rules
sudo udevadm trigger

# Проверяем результат
ls -la /dev/rfid*
```

## Проверка

После установки должны появиться символические ссылки:

```bash
$ ls -la /dev/rfid*
lrwxrwxrwx 1 root root 7 Jan 14 13:16 /dev/rfid_book -> ttyUSB1
lrwxrwxrwx 1 root root 7 Jan 14 13:16 /dev/rfid_uhf_card -> ttyUSB0
```

## Диагностика

### Если символические ссылки не создались

1. **Проверьте подключение устройств:**
   ```bash
   lsusb | grep "Silicon Labs"
   ls -la /dev/ttyUSB*
   ```

2. **Проверьте DEVPATH устройств:**
   ```bash
   for dev in /dev/ttyUSB*; do
       echo "=== $dev ==="
       udevadm info --query=all --name=$dev | grep DEVPATH
   done
   ```

3. **Проверьте применение правил:**
   ```bash
   sudo udevadm test /dev/ttyUSB0
   sudo udevadm test /dev/ttyUSB1
   ```

### Изменение портов

Если устройства подключены в другие USB порты, отредактируйте файл `/etc/udev/rules.d/99-bookcabinet-rfid.rules`:

1. Найдите DEVPATH ваших устройств (см. выше)
2. Замените DEVPATH в правилах на актуальные значения
3. Примените правила заново:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

## Структура DEVPATH

DEVPATH показывает физическое расположение устройства в USB дереве:

```
/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/1-1.5.4/...
                                             └─┬─┘ └─┬─┘
                                              Hub   Port
```

- `1-1` - корневой хаб
- `1-1.5` - внешний USB хаб (если есть)
- `1-1.5.4` - порт 4 на хабе

## Fallback механизм

В `config.py` предусмотрен fallback на прямые порты, если символические ссылки не созданы:

```python
RFID = {
    'uhf_card_reader': '/dev/rfid_uhf_card',  # Основной путь
    'uhf_card_reader_fallback': '/dev/ttyUSB0',  # Запасной путь
    ...
}
```

## Примечания

- Правила привязаны к физическим USB портам, поэтому устройства нужно подключать в те же порты
- Оба CP2102 имеют одинаковый серийный номер, поэтому используется DEVPATH вместо ID_SERIAL
- ACR1281 работает через PC/SC драйвер, а не как serial устройство
