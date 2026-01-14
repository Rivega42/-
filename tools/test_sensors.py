#!/usr/bin/env python3
"""
Диагностика датчиков TCST2103 с логами min/max
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

SAMPLES = 50

# Статистика
stats = {name: {'min': 100, 'max': 0, 'current': 0} for name in SENSORS}

def read_percent(pin):
    readings = sum(GPIO.input(pin) for _ in range(SAMPLES))
    return readings * 100 // SAMPLES

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in SENSORS.values():
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    print("=" * 70)
    print("  ДИАГНОСТИКА ДАТЧИКОВ — логи min/max")
    print("=" * 70)
    print("Формат: имя:текущий% [min-max]")
    print("Ctrl+C для итогов\n")
    
    try:
        while True:
            parts = []
            for name, pin in SENSORS.items():
                pct = read_percent(pin)
                stats[name]['current'] = pct
                stats[name]['min'] = min(stats[name]['min'], pct)
                stats[name]['max'] = max(stats[name]['max'], pct)
                
                s = stats[name]
                parts.append(f"{name}:{pct:3d}% [{s['min']:2d}-{s['max']:3d}]")
            
            print(f"\r{' | '.join(parts)}", end="", flush=True)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("  ИТОГИ (min-max за всё время)")
        print("=" * 70)
        for name in SENSORS:
            s = stats[name]
            spread = s['max'] - s['min']
            if s['min'] >= 95:
                status = "✓ стабильно НАЖАТ"
            elif s['max'] <= 10:
                status = "✓ стабильно ОТКРЫТ"
            elif spread <= 20:
                status = "~ почти стабильно"
            else:
                status = f"✗ МОРГАЕТ (разброс {spread}%)"
            print(f"  {name:12s}: {s['min']:3d}% - {s['max']:3d}%  {status}")
        
        print("\n" + "-" * 70)
        print("Рекомендуемый threshold: выше максимума открытого датчика")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
