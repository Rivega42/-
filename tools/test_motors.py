#!/usr/bin/env python3
"""
Тест шаговых моторов каретки (CoreXY)

Motor A: GPIO 2 (STEP), GPIO 3 (DIR)
Motor B: GPIO 19 (STEP), GPIO 21 (DIR)
Tray:    GPIO 24 (STEP), GPIO 25 (DIR)

CoreXY кинематика:
- X движение: A и B в одном направлении
- Y движение: A и B в разных направлениях
"""
import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run on Raspberry Pi!")
    sys.exit(1)

# Конфигурация пинов
MOTOR_A_STEP = 2
MOTOR_A_DIR = 3
MOTOR_B_STEP = 19
MOTOR_B_DIR = 21
TRAY_STEP = 24
TRAY_DIR = 25

# Направления
DIR_FORWARD = GPIO.HIGH
DIR_BACKWARD = GPIO.LOW

# Скорость (задержка между шагами в секундах)
STEP_DELAY = 0.001  # 1ms = 1000 шагов/сек


def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    for pin in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR, TRAY_STEP, TRAY_DIR]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)


def step_motor(step_pin, steps, delay=STEP_DELAY):
    """Сделать N шагов"""
    for _ in range(steps):
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(delay)


def move_motor_a(steps, direction=DIR_FORWARD):
    """Двигать мотор A"""
    GPIO.output(MOTOR_A_DIR, direction)
    time.sleep(0.001)
    step_motor(MOTOR_A_STEP, abs(steps))


def move_motor_b(steps, direction=DIR_FORWARD):
    """Двигать мотор B"""
    GPIO.output(MOTOR_B_DIR, direction)
    time.sleep(0.001)
    step_motor(MOTOR_B_STEP, abs(steps))


def move_tray(steps, direction=DIR_FORWARD):
    """Двигать платформу"""
    GPIO.output(TRAY_DIR, direction)
    time.sleep(0.001)
    step_motor(TRAY_STEP, abs(steps))


def move_xy_corexy(x_steps, y_steps):
    """
    CoreXY движение
    X: A+B в одном направлении
    Y: A+B в разных направлениях
    
    Упрощённо (без одновременного движения):
    """
    # Движение по X
    if x_steps != 0:
        dir_val = DIR_FORWARD if x_steps > 0 else DIR_BACKWARD
        GPIO.output(MOTOR_A_DIR, dir_val)
        GPIO.output(MOTOR_B_DIR, dir_val)
        time.sleep(0.001)
        
        for _ in range(abs(x_steps)):
            GPIO.output(MOTOR_A_STEP, GPIO.HIGH)
            GPIO.output(MOTOR_B_STEP, GPIO.HIGH)
            time.sleep(STEP_DELAY)
            GPIO.output(MOTOR_A_STEP, GPIO.LOW)
            GPIO.output(MOTOR_B_STEP, GPIO.LOW)
            time.sleep(STEP_DELAY)
    
    # Движение по Y
    if y_steps != 0:
        dir_a = DIR_FORWARD if y_steps > 0 else DIR_BACKWARD
        dir_b = DIR_BACKWARD if y_steps > 0 else DIR_FORWARD  # Инверсия для B
        GPIO.output(MOTOR_A_DIR, dir_a)
        GPIO.output(MOTOR_B_DIR, dir_b)
        time.sleep(0.001)
        
        for _ in range(abs(y_steps)):
            GPIO.output(MOTOR_A_STEP, GPIO.HIGH)
            GPIO.output(MOTOR_B_STEP, GPIO.HIGH)
            time.sleep(STEP_DELAY)
            GPIO.output(MOTOR_A_STEP, GPIO.LOW)
            GPIO.output(MOTOR_B_STEP, GPIO.LOW)
            time.sleep(STEP_DELAY)


def test_single_motor(name, step_fn):
    """Тест одного мотора"""
    print(f"\n{'='*50}")
    print(f"  Testing {name}")
    print(f"{'='*50}")
    
    steps = 200  # 1 оборот для 200 step/rev мотора
    
    input(f"Press Enter to move {name} FORWARD ({steps} steps)...")
    step_fn(steps, DIR_FORWARD)
    print(f"  Done.")
    
    input(f"Press Enter to move {name} BACKWARD ({steps} steps)...")
    step_fn(steps, DIR_BACKWARD)
    print(f"  Done.")


def interactive_mode():
    """Интерактивный режим"""
    print("\n" + "="*50)
    print("  INTERACTIVE MODE")
    print("="*50)
    print("Commands:")
    print("  a+ / a-   — Motor A forward/backward (200 steps)")
    print("  b+ / b-   — Motor B forward/backward")
    print("  t+ / t-   — Tray forward/backward")
    print("  x+ / x-   — CoreXY X axis")
    print("  y+ / y-   — CoreXY Y axis")
    print("  a:500     — Motor A 500 steps forward")
    print("  a:-500    — Motor A 500 steps backward")
    print("  s:0.002   — Set step delay (slower)")
    print("  q         — Quit")
    print()
    
    global STEP_DELAY
    default_steps = 200
    
    while True:
        try:
            cmd = input("Command: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        
        if cmd == 'q':
            break
        elif cmd == 'a+':
            print(f"  Motor A forward {default_steps} steps...")
            move_motor_a(default_steps, DIR_FORWARD)
        elif cmd == 'a-':
            print(f"  Motor A backward {default_steps} steps...")
            move_motor_a(default_steps, DIR_BACKWARD)
        elif cmd == 'b+':
            print(f"  Motor B forward {default_steps} steps...")
            move_motor_b(default_steps, DIR_FORWARD)
        elif cmd == 'b-':
            print(f"  Motor B backward {default_steps} steps...")
            move_motor_b(default_steps, DIR_BACKWARD)
        elif cmd == 't+':
            print(f"  Tray forward {default_steps} steps...")
            move_tray(default_steps, DIR_FORWARD)
        elif cmd == 't-':
            print(f"  Tray backward {default_steps} steps...")
            move_tray(default_steps, DIR_BACKWARD)
        elif cmd == 'x+':
            print(f"  CoreXY X+ {default_steps} steps...")
            move_xy_corexy(default_steps, 0)
        elif cmd == 'x-':
            print(f"  CoreXY X- {default_steps} steps...")
            move_xy_corexy(-default_steps, 0)
        elif cmd == 'y+':
            print(f"  CoreXY Y+ {default_steps} steps...")
            move_xy_corexy(0, default_steps)
        elif cmd == 'y-':
            print(f"  CoreXY Y- {default_steps} steps...")
            move_xy_corexy(0, -default_steps)
        elif cmd.startswith('s:'):
            try:
                STEP_DELAY = float(cmd[2:])
                print(f"  Step delay = {STEP_DELAY} sec")
            except ValueError:
                print("  Invalid delay value")
        elif ':' in cmd:
            try:
                motor, steps = cmd.split(':')
                steps = int(steps)
                direction = DIR_FORWARD if steps >= 0 else DIR_BACKWARD
                steps = abs(steps)
                
                if motor == 'a':
                    print(f"  Motor A {steps} steps...")
                    move_motor_a(steps, direction)
                elif motor == 'b':
                    print(f"  Motor B {steps} steps...")
                    move_motor_b(steps, direction)
                elif motor == 't':
                    print(f"  Tray {steps} steps...")
                    move_tray(steps, direction)
                else:
                    print("  Unknown motor. Use a, b, or t")
            except ValueError:
                print("  Invalid format. Use: a:500 or t:-200")
        else:
            print("  Unknown command")


def main():
    print("="*50)
    print("  STEPPER MOTOR TEST")
    print("="*50)
    print(f"Motor A: STEP=GPIO{MOTOR_A_STEP}, DIR=GPIO{MOTOR_A_DIR}")
    print(f"Motor B: STEP=GPIO{MOTOR_B_STEP}, DIR=GPIO{MOTOR_B_DIR}")
    print(f"Tray:    STEP=GPIO{TRAY_STEP}, DIR=GPIO{TRAY_DIR}")
    print(f"Step delay: {STEP_DELAY} sec")
    
    setup()
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == '-i':
            interactive_mode()
        else:
            test_single_motor("Motor A", move_motor_a)
            test_single_motor("Motor B", move_motor_b)
            test_single_motor("Tray", move_tray)
            
            print("\n" + "="*50)
            print("  Run with -i for interactive mode")
            print("="*50)
    finally:
        GPIO.cleanup()
        print("\nGPIO cleanup done.")


if __name__ == '__main__':
    main()
