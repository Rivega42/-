# Управление шаговым двигателем платформы (Tray)

## Файл управления
`~/bookcabinet/tools/tray_platform.py`

## GPIO пины (BCM)
| Функция | Pin | Описание |
|---------|-----|----------|
| TRAY_STEP | 18 | Импульсы шага |
| TRAY_DIR | 27 | Направление: 0=FRONT, 1=BACK |
| TRAY_EN1 | 25 | Enable: LOW=работа |
| TRAY_EN2 | 26 | Enable: LOW=работа |
| ENDSTOP_FRONT | 7 | 1=нажат |
| ENDSTOP_BACK | 20 | 1=нажат |

## Команды
```bash
python3 tools/tray_platform.py status     # Состояние концевиков
python3 tools/tray_platform.py front      # К переднему концевику
python3 tools/tray_platform.py back       # К заднему концевику
python3 tools/tray_platform.py calibrate  # FRONT → BACK → CENTER
python3 tools/tray_platform.py center     # В центр (после calibrate)
```

## Параметры
- **Частота:** 12000 Hz
- **Total travel:** ~21000 шагов
- **Center:** ~10500 шагов
- **Метод:** pigpio wave (аппаратные импульсы)

## Важно
- Enable пины: LOW для работы, HIGH для отключения
- Glitch filter: 1000μs на концевиках (против помех от мотора)
- После калибровки драйвер автоматически отключается (EN=HIGH)
- Резисторы на концевиках убирают помехи от шагового двигателя
