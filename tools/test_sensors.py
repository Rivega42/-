#!/usr/bin/env python3
"""
Тестирование датчиков и концевиков BookCabinet
Отображает состояние в реальном времени

Запуск: python3 tools/test_sensors.py
"""
import RPi.GPIO as GPIO
import time
import sys

# Датчики из config.py
SENSORS = {
    'X_BEGIN': 10,    # Левый концевик (MOSI)
    'X_END': 9,       # Правый концевик (MISO)
    'Y_BEGIN': 11,    # Нижний концевик (SCLK)
    'Y_END': 8,       # Верхний концевик (CE0)
    'TRAY_BEGIN': 7,  # Платформа назад (CE1)
    'TRAY_END': 20,   # Платформа вперёд (PCMi)
}

def test_with_pullup():
    """Тест с подтяжкой к VCC (PUD_UP)"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("\n=== Тест с PUD_UP ===")
    print("Ожидание: свободен=1, нажат=0")
    results = {}
    for name, pin in SENSORS.items():
        val = GPIO.input(pin)
        results[name] = val
        print(f"  {name} (GPIO{pin}): {val}")
    GPIO.cleanup()
    return results

def test_with_pulldown():
    """Тест с подтяжкой к GND (PUD_DOWN)"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
    print("\n=== Тест с PUD_DOWN ===")
    print("Ожидание: свободен=0, нажат=1")
    results = {}
    for name, pin in SENSORS.items():
        val = GPIO.input(pin)
        results[name] = val
        print(f"  {name} (GPIO{pin}): {val}")
    GPIO.cleanup()
    return results

def monitor(pull_mode='DOWN'):
    """Мониторинг в реальном времени"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    pud = GPIO.PUD_DOWN if pull_mode == 'DOWN' else GPIO.PUD_UP
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
    
    print(f"\n=== Мониторинг с PUD_{pull_mode} ===")
    if pull_mode == 'DOWN':
        print("Логика: HIGH(1)=СРАБОТАЛ, LOW(0)=свободен")
    else:
        print("Логика: LOW(0)=СРАБОТАЛ, HIGH(1)=свободен")
    print("Ctrl+C для выхода\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                val = GPIO.input(pin)
                if pull_mode == 'DOWN':
                    icon = "🔴" if val == 1 else "⚪"
                else:
                    icon = "🔴" if val == 0 else "⚪"
                parts.append(f"{name}:{icon}({val})")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\n")
    finally:
        GPIO.cleanup()

def main():
    print("=" * 60)
    print("  ДИАГНОСТИКА ДАТЧИКОВ BookCabinet")
    print("=" * 60)
    
    # Однократное чтение с обеими подтяжками
    up_results = test_with_pullup()
    time.sleep(0.5)
    down_results = test_with_pulldown()
    
    # Анализ
    print("\n" + "=" * 60)
    print("  АНАЛИЗ")
    print("=" * 60)
    
    # Если с PUD_DOWN стабильнее - датчики подключены к VCC
    # Если с PUD_UP стабильнее - датчики подключены к GND
    
    print("\nY_END (каретка внизу, датчик нажат):")
    print(f"  PUD_UP:   {up_results['Y_END']}")
    print(f"  PUD_DOWN: {down_results['Y_END']}")
    
    if down_results['Y_END'] == 1:
        print("\n✓ Датчики подключены к VCC при срабатывании")
        print("  Рекомендация: использовать PUD_DOWN")
        print("\nЗапускаю мониторинг с PUD_DOWN...")
        time.sleep(2)
        monitor('DOWN')
    elif up_results['Y_END'] == 0:
        print("\n✓ Датчики подключены к GND при срабатывании")
        print("  Рекомендация: использовать PUD_UP")
        print("\nЗапускаю мониторинг с PUD_UP...")
        time.sleep(2)
        monitor('UP')
    else:
        print("\n? Не удалось определить тип подключения")
        print("  Запускаю мониторинг с PUD_DOWN (попробуем)...")
        time.sleep(2)
        monitor('DOWN')

if __name__ == '__main__':
    main()
