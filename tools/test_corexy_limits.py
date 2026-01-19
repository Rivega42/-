#!/usr/bin/env python3
"""
Тест CoreXY моторов с концевиками.

Управление:
  W/S - движение по Y (вверх/вниз)
  A/D - движение по X (влево/вправо)
  Q   - выход

Логика: движение блокируется только если едем В датчик,
а не ОТ него. Это позволяет съехать с концевика.

Запуск:
  python3 tools/test_corexy_limits.py
"""

import RPi.GPIO as GPIO
import time
import sys
import tty
import termios
import select

# === GPIO пины ===
# Моторы
MOTOR_A_STEP = 2
MOTOR_A_DIR = 3
MOTOR_B_STEP = 19
MOTOR_B_DIR = 21

# Концевики (HIGH = сработал!)
SENSOR_LEFT = 9
SENSOR_RIGHT = 10
SENSOR_BOTTOM = 8
SENSOR_TOP = 11

# Параметры
STEP_DELAY = 0.002
STEPS_PER_MOVE = 50


def setup_gpio():
    """Инициализация GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Моторы - выходы
    for pin in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    
    # Датчики - входы с подтяжкой
    for pin in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def read_sensors():
    """Чтение датчиков (True = сработал)"""
    return {
        'left': GPIO.input(SENSOR_LEFT) == GPIO.HIGH,
        'right': GPIO.input(SENSOR_RIGHT) == GPIO.HIGH,
        'bottom': GPIO.input(SENSOR_BOTTOM) == GPIO.HIGH,
        'top': GPIO.input(SENSOR_TOP) == GPIO.HIGH,
    }


def step_motors(a_dir, b_dir, steps, block_sensor=None):
    """
    Шаги моторов CoreXY.
    
    CoreXY логика:
      X+ (вправо): A+, B+
      X- (влево):  A-, B-
      Y+ (вверх):  A+, B-
      Y- (вниз):   A-, B+
    
    Args:
        a_dir: направление мотора A (1/0)
        b_dir: направление мотора B (1/0)
        steps: количество шагов
        block_sensor: имя датчика который блокирует движение
    
    Returns:
        имя сработавшего датчика или None
    """
    GPIO.output(MOTOR_A_DIR, a_dir)
    GPIO.output(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)
    
    for _ in range(steps):
        # Проверяем только датчик в направлении движения
        if block_sensor:
            sensors = read_sensors()
            if sensors.get(block_sensor):
                return block_sensor
        
        # Шаг обоих моторов
        GPIO.output(MOTOR_A_STEP, GPIO.HIGH)
        GPIO.output(MOTOR_B_STEP, GPIO.HIGH)
        time.sleep(STEP_DELAY)
        GPIO.output(MOTOR_A_STEP, GPIO.LOW)
        GPIO.output(MOTOR_B_STEP, GPIO.LOW)
        time.sleep(STEP_DELAY)
    
    return None


def move_up(steps=STEPS_PER_MOVE):
    """Вверх - блокируем только TOP"""
    return step_motors(1, 0, steps, 'top')


def move_down(steps=STEPS_PER_MOVE):
    """Вниз - блокируем только BOTTOM"""
    return step_motors(0, 1, steps, 'bottom')


def move_left(steps=STEPS_PER_MOVE):
    """Влево - блокируем только LEFT"""
    return step_motors(0, 0, steps, 'left')


def move_right(steps=STEPS_PER_MOVE):
    """Вправо - блокируем только RIGHT"""
    return step_motors(1, 1, steps, 'right')


def print_status():
    """Вывод состояния датчиков"""
    s = read_sensors()
    active = [k.upper() for k, v in s.items() if v]
    print(f"  [{' '.join(active) if active else '---'}]")


def get_key():
    """Неблокирующее чтение клавиши"""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).lower()
    return None


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║            ТЕСТ CoreXY С КОНЦЕВИКАМИ                         ║
╠══════════════════════════════════════════════════════════════╣
║  Управление:                                                 ║
║    W - вверх      S - вниз                                   ║
║    A - влево      D - вправо                                 ║
║    Q - выход                                                 ║
║                                                              ║
║  Движение блокируется только если едем В датчик!             ║
║  Можно съехать с концевика в противоположную сторону.        ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    setup_gpio()
    
    # Сохраняем настройки терминала
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        print("Готов. WASD=движение, Q=выход\n")
        print_status()
        
        while True:
            key = get_key()
            
            if key == 'q':
                print("\nВыход...")
                break
            
            triggered = None
            
            if key == 'w':
                print("UP...", end=' ', flush=True)
                triggered = move_up()
                print("STOP" if triggered else "ok")
                
            elif key == 's':
                print("DOWN...", end=' ', flush=True)
                triggered = move_down()
                print("STOP" if triggered else "ok")
                
            elif key == 'a':
                print("LEFT...", end=' ', flush=True)
                triggered = move_left()
                print("STOP" if triggered else "ok")
                
            elif key == 'd':
                print("RIGHT...", end=' ', flush=True)
                triggered = move_right()
                print("STOP" if triggered else "ok")
            
            if key in ['w', 'a', 's', 'd']:
                print_status()
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\nПрервано")
    
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        GPIO.cleanup()
        print("GPIO cleanup done")


if __name__ == "__main__":
    main()
