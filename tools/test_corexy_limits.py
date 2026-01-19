#!/usr/bin/env python3
"""
Тест CoreXY моторов с концевиками.

Управление:
  W/S - движение по Y (вверх/вниз)
  A/D - движение по X (влево/вправо)
  Q   - выход

При срабатывании концевика - автостоп и отскок назад.

Запуск:
  python3 tools/test_corexy_limits.py
"""

import RPi.GPIO as GPIO
import time
import sys
import select
import tty
import termios

# === GPIO пины ===
# Моторы
MOTOR_A_STEP = 2
MOTOR_A_DIR = 3
MOTOR_B_STEP = 19
MOTOR_B_DIR = 21

# Концевики (HIGH = сработал!) - РЕАЛЬНАЯ МАППИРОВКА
SENSOR_X_BEGIN = 9   # левый
SENSOR_X_END = 10    # правый
SENSOR_Y_BEGIN = 8   # нижний
SENSOR_Y_END = 11    # верхний

# Параметры движения
STEP_DELAY = 0.002  # задержка между шагами (сек)
STEPS_PER_MOVE = 50  # шагов за одно нажатие
BOUNCE_STEPS = 100   # шагов отскока от концевика


def setup_gpio():
    """Инициализация GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Моторы - выходы
    for pin in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    
    # Концевики - входы с подтяжкой
    for pin in [SENSOR_X_BEGIN, SENSOR_X_END, SENSOR_Y_BEGIN, SENSOR_Y_END]:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def read_sensors():
    """Чтение состояния концевиков (True = сработал)"""
    # HIGH = сработал!
    return {
        'x_begin': GPIO.input(SENSOR_X_BEGIN) == GPIO.HIGH,
        'x_end': GPIO.input(SENSOR_X_END) == GPIO.HIGH,
        'y_begin': GPIO.input(SENSOR_Y_BEGIN) == GPIO.HIGH,
        'y_end': GPIO.input(SENSOR_Y_END) == GPIO.HIGH,
    }


def step_motors(a_dir, b_dir, steps, check_sensors=True):
    """
    Шаги моторов CoreXY.
    
    CoreXY логика:
      X+ (вправо): A+, B+
      X- (влево):  A-, B-
      Y+ (вверх):  A+, B-
      Y- (вниз):   A-, B+
    
    Args:
        a_dir: направление мотора A (1=вперёд, 0=назад)
        b_dir: направление мотора B (1=вперёд, 0=назад)
        steps: количество шагов
        check_sensors: проверять концевики
    
    Returns:
        sensor_name если сработал концевик, иначе None
    """
    GPIO.output(MOTOR_A_DIR, a_dir)
    GPIO.output(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)
    
    for _ in range(steps):
        # Проверка концевиков
        if check_sensors:
            sensors = read_sensors()
            for name, triggered in sensors.items():
                if triggered:
                    return name
        
        # Шаг обоих моторов одновременно
        GPIO.output(MOTOR_A_STEP, GPIO.HIGH)
        GPIO.output(MOTOR_B_STEP, GPIO.HIGH)
        time.sleep(STEP_DELAY)
        GPIO.output(MOTOR_A_STEP, GPIO.LOW)
        GPIO.output(MOTOR_B_STEP, GPIO.LOW)
        time.sleep(STEP_DELAY)
    
    return None


def move_x(direction, steps=STEPS_PER_MOVE):
    """Движение по X. direction: 1=вправо, -1=влево"""
    if direction > 0:  # вправо
        return step_motors(1, 1, steps)
    else:  # влево
        return step_motors(0, 0, steps)


def move_y(direction, steps=STEPS_PER_MOVE):
    """Движение по Y. direction: 1=вверх, -1=вниз"""
    if direction > 0:  # вверх
        return step_motors(1, 0, steps)
    else:  # вниз
        return step_motors(0, 1, steps)


def bounce_from_sensor(sensor_name):
    """Отскок от сработавшего концевика"""
    print(f"  ! {sensor_name} - отскок...", end=' ', flush=True)
    
    # Определяем направление отскока (без проверки датчиков!)
    if sensor_name == 'x_begin':  # левый - едем вправо
        step_motors(1, 1, BOUNCE_STEPS, check_sensors=False)
    elif sensor_name == 'x_end':  # правый - едем влево
        step_motors(0, 0, BOUNCE_STEPS, check_sensors=False)
    elif sensor_name == 'y_begin':  # нижний - едем вверх
        step_motors(1, 0, BOUNCE_STEPS, check_sensors=False)
    elif sensor_name == 'y_end':  # верхний - едем вниз
        step_motors(0, 1, BOUNCE_STEPS, check_sensors=False)
    
    print("ok")


def get_key():
    """Неблокирующее чтение клавиши"""
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1).lower()
    return None


def print_status():
    """Вывод состояния датчиков"""
    s = read_sensors()
    status = []
    if s['x_begin']: status.append('LEFT!')
    if s['x_end']: status.append('RIGHT!')
    if s['y_begin']: status.append('BOTTOM!')
    if s['y_end']: status.append('TOP!')
    
    if status:
        print(f"  Датчики: {', '.join(status)}")
    else:
        print("  Датчики: ---")
    return s


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
║  При срабатывании концевика - автоматический отскок!         ║
║                                                              ║
║  Датчики: HIGH = сработал                                    ║
║    LEFT=GPIO9  RIGHT=GPIO10  BOTTOM=GPIO8  TOP=GPIO11       ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    setup_gpio()
    
    # Сохраняем настройки терминала
    old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        # Переключаем терминал в raw режим
        tty.setcbreak(sys.stdin.fileno())
        
        print("Готов. Жми WASD для движения, Q для выхода.\n")
        print_status()
        
        while True:
            key = get_key()
            
            if key == 'q':
                print("\nВыход...")
                break
            
            triggered = None
            
            if key == 'w':
                print("Y+ (вверх)...", end=' ', flush=True)
                triggered = move_y(1)
                print("ok" if not triggered else "")
                
            elif key == 's':
                print("Y- (вниз)...", end=' ', flush=True)
                triggered = move_y(-1)
                print("ok" if not triggered else "")
                
            elif key == 'a':
                print("X- (влево)...", end=' ', flush=True)
                triggered = move_x(-1)
                print("ok" if not triggered else "")
                
            elif key == 'd':
                print("X+ (вправо)...", end=' ', flush=True)
                triggered = move_x(1)
                print("ok" if not triggered else "")
            
            # Если сработал концевик - отскок
            if triggered:
                bounce_from_sensor(triggered)
            
            # Показать статус датчиков
            if key in ['w', 'a', 's', 'd']:
                print_status()
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("\n\nПрервано")
    
    finally:
        # Восстанавливаем терминал
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        GPIO.cleanup()
        print("GPIO cleanup done")


if __name__ == "__main__":
    main()
