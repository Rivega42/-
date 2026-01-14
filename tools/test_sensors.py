#!/usr/bin/env python3
"""
Диагностика сырых значений датчиков TCST2103
Показывает % HIGH за последнюю секунду
"""
import RPi.GPIO as GPIO
import time
from collections import deque

SENSORS = {
    'X_BEGIN': 10,
    'X_END': 9,
    'Y_BEGIN': 11,
    'Y_END': 8,
    'TRAY_BEGIN': 7,
    'TRAY_END': 20,
}

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Пробуем без подтяжки - читаем что реально даёт датчик
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
    
    print("=" * 65)
    print("  ДИАГНОСТИКА ДАТЧИКОВ (без подтяжки RPi)")
    print("=" * 65)
    print("Показывает % времени в HIGH за последние 100 чтений")
    print("100% = всегда HIGH | 0% = всегда LOW | 50% = моргает")
    print("Ctrl+C для выхода\n")
    
    # История последних 100 чтений
    history = {name: deque(maxlen=100) for name in SENSORS}
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                val = GPIO.input(pin)
                history[name].append(val)
                
                if len(history[name]) >= 10:
                    pct = sum(history[name]) * 100 // len(history[name])
                    # Интерпретация
                    if pct >= 95:
                        status = f"🔴{pct:3d}%"  # Стабильно HIGH
                    elif pct <= 5:
                        status = f"⚪{pct:3d}%"  # Стабильно LOW
                    else:
                        status = f"❓{pct:3d}%"  # Нестабильно
                else:
                    status = " ... "
                    
                parts.append(f"{name}:{status}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n--- ИНТЕРПРЕТАЦИЯ ---")
        print("🔴 95-100% = нажат (или проблема с датчиком)")
        print("⚪ 0-5%    = свободен (норма)")
        print("❓ 6-94%   = нестабильно (проблема: наводки/питание/подключение)")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
