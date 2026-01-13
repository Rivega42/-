# Project Instructions для Claude

> Скопируй текст ниже в настройки проекта (Project Instructions)

---

К проекту подключен репозиторий: github.com/Rivega42/-

В НАЧАЛЕ СЕССИИ:
Прочитай ТОЛЬКО файл QUICKSTART.md в корне репозитория.
НЕ читай другие файлы пока пользователь не попросит.

СРЕДА:
- Windows 11, PowerShell / Windows Terminal
- Raspberry Pi 3 — целевая система (всё на одном устройстве!)
- SSH: admin42@10.10.31.12 (или admin42@Shkaf)
- Python на RPi: python3 (не py)
- Репозиторий на RPi: ~/bookcabinet/

ИЗВЕСТНЫЕ РЕШЕНИЯ (применять сразу):
- WiFi не работает → слабый БП, нужен 5V/2.5A+ (vcgencmd get_throttled)
- RFID UHF молчит → протокол 0xA0, НЕ 0x04! checksum = (~SUM+1)&0xFF
- Датчики врут → инверсия логики (LOW = нажат, не HIGH)
- Замки путаница → Open=язычок ОПУЩЕН, Close=ПОДНЯТ (инверсия терминологии!)
- GPIO не реагирует → проверь config.py + sudo systemctl restart shelf-server
- Резисторы для датчиков → НЕ нужны, используй GPIO.PUD_UP

ОБОРУДОВАНИЕ:
- ACR1281U-C → карты (билет + ЕКП), NFC 13.56MHz, работает
- IQRFID-5102 → книжные метки, UHF 900MHz, протокол 0xA0
- RRU9816 → требует Windows DLL, планируется замена

ССЫЛКИ:
- Референс ИРБИС: github.com/valinerosgordov/RFIDShkafWithIRBIS
- ИРБИС API: TCP порт 6666, кодировка cp1251

ДОКУМЕНТАЦИЯ (читать при необходимости):
- docs/TODO.md — текущие задачи
- docs/DEVLOG.md — история решений (поиск по тегам: [rfid], [gpio], [rpi]...)
- docs/DECISIONS.md — почему так решили
- docs/GLOSSARY.md — терминология (инверсии!)
- docs/HARDWARE.md — инвентарь оборудования
- docs/TROUBLESHOOTING.md — проблемы требующие физ. доступа

В КОНЦЕ СЕССИИ:
1. Обнови docs/TODO.md — отметь выполненное, добавь новые задачи
2. Добавь запись в docs/DEVLOG.md — что делали и на чём остановились (с тегами!)
