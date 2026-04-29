# 📚 BookCabinet — База знаний

Добро пожаловать в базу знаний проекта **BookCabinet** — автоматического шкафа книговыдачи на Raspberry Pi + CoreXY.

---

## 🚀 Быстрый старт

### Подключение к шкафу

```bash
ssh admin42@2.56.241.126 -p 2222
```

### Первый запуск после подключения

```bash
cd ~/bookcabinet
# Полная инициализация: хоминг XY + калибровка лотка
python3 ~/bookcabinet/tools/startup_sequence.py
```

### Выдать книгу вручную (пример)

```bash
# Переместить каретку к ячейке 2.1.16, извлечь полочку из заднего ряда
python3 ~/bookcabinet/tools/move_shelf.py 2.1.16 1.2.9
```

---

## 🗺️ Карта документов

| Файл | Описание |
|------|----------|
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Шпаргалка всех команд с примерами — начни отсюда |
| **[SCRIPTS.md](SCRIPTS.md)** | Подробное описание каждого скрипта в `tools/` |
| **[HARDWARE.md](HARDWARE.md)** | Карта пинов GPIO, моторы, замки, шторки, концевики |
| **[SHELF_OPERATIONS.md](SHELF_OPERATIONS.md)** | Алгоритмы работы с полочками — замки, перехваты, последовательности |
| **[ISSUE_BOOK_WORKFLOW.md](ISSUE_BOOK_WORKFLOW.md)** | Полный цикл выдачи книги (issue #79) с диаграммами |
| **[RETURN_BOOK_WORKFLOW.md](RETURN_BOOK_WORKFLOW.md)** | Полный цикл возврата книги (issue #80) с диаграммами |
| **[CALIBRATION.md](CALIBRATION.md)** | Формат calibration.json и процесс калибровки |
| **[STARTUP.md](STARTUP.md)** | Старт системы: systemd → main.py → StartupRecovery |
| **[RFID.md](RFID.md)** | Все считыватели: NFC ACR1281, UHF IQRFID-5102 (книги/ЕКП), UnifiedReader, RRU9816 |
| **[IRBIS.md](IRBIS.md)** | ИРБИС64: протокол TCP, LibraryService, offline очередь, mock режим |

---

## 📐 Формат адреса ячейки

```
depth.rack.shelf
  │     │    └── Полка: 1–21 (снизу вверх)
  │     └── Стойка: 1, 2, 3 (слева направо)
  └── Глубина: 1 = передний ряд, 2 = задний ряд
```

**Примеры:**
- `1.2.9` — передний ряд, стойка 2, полка 9 (окно выдачи)
- `2.1.16` — задний ряд, стойка 1, полка 16

---

## 🔑 Ключевые факты

- **Шкаф:** 3 стойки × 21 полка × 2 ряда = 126 ячеек
- **Окно выдачи:** `1.2.9` (фиксировано в калибровке)
- **Хоминг:** LEFT_BOTTOM (X=0, Y=0 — левый нижний угол)
- **Лоток:** total=22467 шагов, center=11233, freq=12000Hz
- **SSH:** `admin42@2.56.241.126 -p 2222`
- **Веб-интерфейс:** `http://2.56.241.126:5000`

---

## 🧭 Быстрая навигация по задачам

**Нужно выдать книгу вручную?** → [QUICK_REFERENCE.md#выдача](QUICK_REFERENCE.md)

**Разбираешься с замками?** → [SHELF_OPERATIONS.md](SHELF_OPERATIONS.md)

**Настраиваешь железо?** → [HARDWARE.md](HARDWARE.md)

**Изучаешь workflow выдачи?** → [ISSUE_BOOK_WORKFLOW.md](ISSUE_BOOK_WORKFLOW.md)

**RFID не читает?** → [RFID.md](RFID.md)

**ИРБИС не отвечает?** → [IRBIS.md](IRBIS.md)

**Проблема при старте?** → [STARTUP.md](STARTUP.md)

**Нужна калибровка?** → [CALIBRATION.md](CALIBRATION.md)
