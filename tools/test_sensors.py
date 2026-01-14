#!/usr/bin/env python3
"""
Тестирование оптических датчиков TCST2103
Щелевые оптопары с открытым коллектором

Запуск: python3 tools/test_sensors.py
"""
import RPi.GPIO as GPIO
import time

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
    
    # TCST2103 = открытый коллектор, нужен PUD_UP!
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 60)
    print("  ТЕСТ ДАТЧИКОВ TCST2103 (оптопары)")
    print("=" * 60)
    print("PUD_UP | Щель открыта=LOW(0)⚪ | Щель закрыта=HIGH(1)🔴")
    print("Ctrl+C для выхода\n")
    
    # Состояние с фильтром
    state = {name: 0 for name in SENSORS}
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                # Фильтр: 10 чтений, нужно 8+ для смены
                readings = sum(GPIO.input(pin) for _ in range(10))
                if readings >= 8:
                    state[name] = 1
                elif readings <= 2:
                    state[name] = 0
                    
                icon = "🔴" if state[name] == 1 else "⚪"
                parts.append(f"{name}:{icon}")
            
            print(f"\r{' | '.join(parts)}    ", end="", flush=True)
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
