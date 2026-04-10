#!/usr/bin/env python3
"""Хоминг Y — wave_chain + callback."""
import pigpio, time, sys

MOTOR_A_STEP = 14; MOTOR_A_DIR = 15
MOTOR_B_STEP = 19; MOTOR_B_DIR = 21
SENSOR_BOTTOM = 8; SENSOR_TOP = 11

FAST = 5000   # снижено с 12000 — мотор может stall на длинных волнах
SLOW = 600
BACK = 1000
WAVE_SEG = 200

pi = pigpio.pi()
if not pi.connected: sys.exit("pigpiod!")

for p in [14,15,19,21]:
    pi.set_mode(p, pigpio.OUTPUT); pi.write(p, 0)
for p in [8, 11]:
    pi.set_mode(p, pigpio.INPUT); pi.set_pull_up_down(p, pigpio.PUD_UP)

STEP_MASK = (1 << 14) | (1 << 19)
hit = False

def on_hit(gpio, level, tick):
    global hit
    if not hit:
        hit = True
        pi.wave_tx_stop()
        print(f"  >> СТОП pin {gpio}")

def send_steps(a_dir, b_dir, steps, speed):
    """N шагов без датчиков. Разбивает на сегменты по WAVE_SEG."""
    if a_dir == 0 and b_dir == 1 and pi.read(8) == 1:
        print("  ⛔ BOTTOM нажат!"); return
    if a_dir == 1 and b_dir == 0 and pi.read(11) == 1:
        print("  ⛔ TOP нажат!"); return

    pi.write(MOTOR_A_DIR, a_dir)
    pi.write(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)

    half = int(1_000_000 / (2 * speed))
    done = 0
    while done < steps:
        chunk = min(WAVE_SEG, steps - done)
        pulses = []
        for _ in range(chunk):
            pulses.append(pigpio.pulse(STEP_MASK, 0, half))
            pulses.append(pigpio.pulse(0, STEP_MASK, half))
        pi.wave_clear()
        pi.wave_add_generic(pulses)
        wid = pi.wave_create()
        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.005)
        pi.wave_delete(wid)
        pi.wave_clear()
        done += chunk

def move_to_sensor(a_dir, b_dir, speed, sensor, max_steps=100000):
    """К датчику через wave_chain + callback."""
    global hit
    hit = False
    if pi.read(sensor) == 1:
        print(f"  ⛔ pin {sensor} уже нажат!"); return False

    pi.write(MOTOR_A_DIR, a_dir)
    pi.write(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)

    cb = pi.callback(sensor, pigpio.RISING_EDGE, on_hit)
    half = int(1_000_000 / (2 * speed))
    pulses = []
    for _ in range(WAVE_SEG):
        pulses.append(pigpio.pulse(STEP_MASK, 0, half))
        pulses.append(pigpio.pulse(0, STEP_MASK, half))
    pi.wave_clear()
    pi.wave_add_generic(pulses)
    wid = pi.wave_create()

    reps = max(1, max_steps // WAVE_SEG)
    chain = bytes([255, 0, wid, 255, 1, reps & 0xFF, (reps >> 8) & 0xFF])
    pi.wave_chain(chain)

    t0 = time.time()
    while pi.wave_tx_busy():
        time.sleep(0.002)
        if time.time() - t0 > 30:
            pi.wave_tx_stop(); break

    cb.cancel()
    pi.wave_delete(wid)
    pi.wave_clear()
    return hit

def main():
    print("=" * 50)
    print("  ХОМИНГ Y")
    print("=" * 50)
    print(f"  BOTTOM={pi.read(8)} TOP={pi.read(11)}")

    if pi.read(8) == 1:
        print(f"\n  Отъезд вверх {BACK} шагов...")
        send_steps(1, 0, BACK, FAST)
        time.sleep(0.2)
        print(f"  BOTTOM={pi.read(8)}")
        if pi.read(8) == 1:
            print("  ✗ Не отъехал!"); pi.stop(); return

    print(f"\n  Фаза 1: Y→BOTTOM ({FAST} шаг/сек)...")
    if not move_to_sensor(0, 1, FAST, 8):
        print("  ✗ Нет"); pi.stop(); return
    print("  ✓ Найден!")

    print(f"\n  Отъезд {BACK} шагов...")
    send_steps(1, 0, BACK, FAST)
    time.sleep(0.2)
    print(f"  BOTTOM={pi.read(8)}")

    print(f"\n  Фаза 2: Y→BOTTOM ({SLOW} шаг/сек)...")
    if move_to_sensor(0, 1, SLOW, 8, max_steps=BACK + 1000):
        print("  ✓ HOME Y!")
    else:
        print("  ✗ Не нашёл")

    pi.stop()
    print("\nГОТОВО")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        pi.wave_tx_stop(); pi.stop(); print("\nПрервано")
