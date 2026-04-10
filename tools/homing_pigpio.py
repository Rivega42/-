#!/usr/bin/env python3
"""
homing_pigpio.py v3 — хоминг BookCabinet через pigpio DMA.
Концевики проверены вручную 23.03.2026:
  LEFT=9, RIGHT=10, BOTTOM=8, TOP=11
  нажат=1, свободен=0, PUD_OFF
HOME = LEFT + BOTTOM
"""
import pigpio
import time
import sys

# === Пины моторов ===
MOTOR_A_STEP = 14
MOTOR_A_DIR  = 15
MOTOR_B_STEP = 19
MOTOR_B_DIR  = 21

# === Концевики (нажат=1, свободен=0) ===
SENSOR_LEFT   = 9
SENSOR_RIGHT  = 10
SENSOR_BOTTOM = 8
SENSOR_TOP    = 11

# === Параметры ===
FAST     = 1500
SLOW     = 400
BACKOFF  = 300
WAVE_SEG = 200

STEP_MASK = (1 << MOTOR_A_STEP) | (1 << MOTOR_B_STEP)

# Направления CoreXY:
# X вправо: A=1 B=1 | X влево: A=0 B=0
# Y вверх:  A=1 B=0 | Y вниз:  A=0 B=1

pi = pigpio.pi()
if not pi.connected:
    sys.exit("ОШИБКА: pigpiod не запущен! sudo pigpiod")

for p in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
    pi.set_mode(p, pigpio.OUTPUT)
    pi.write(p, 0)
for p in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
    pi.set_mode(p, pigpio.INPUT)
    pi.set_pull_up_down(p, pigpio.PUD_OFF)

# Glitch filter на все концевики
pi.set_glitch_filter(SENSOR_LEFT,   300)
pi.set_glitch_filter(SENSOR_RIGHT,  300)
pi.set_glitch_filter(SENSOR_BOTTOM, 300)
pi.set_glitch_filter(SENSOR_TOP,    300)

_hit = False

def _on_endstop(gpio, level, tick):
    global _hit
    if not _hit:
        _hit = True
        pi.wave_tx_stop()


def move(a_dir, b_dir, n, speed, stop_sensor=None):
    global _hit
    _hit = False

    pi.write(MOTOR_A_DIR, a_dir)
    pi.write(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)

    # Если концевик уже нажат — сразу True
    if stop_sensor is not None and pi.read(stop_sensor) == 1:
        return True

    cb = None
    if stop_sensor is not None:
        cb = pi.callback(stop_sensor, pigpio.RISING_EDGE, _on_endstop)

    half_us = int(1_000_000 / (2 * speed))
    pulses = []
    for _ in range(WAVE_SEG):
        pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
        pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
    pi.wave_clear()
    pi.wave_add_generic(pulses)
    wid = pi.wave_create()
    if wid < 0:
        if cb: cb.cancel()
        raise RuntimeError(f"wave_create error: {wid}")

    reps = max(1, n // WAVE_SEG)
    chain = bytes([255, 0, wid, 255, 1, reps & 0xFF, (reps >> 8) & 0xFF])
    pi.wave_chain(chain)

    t0 = time.time()
    while pi.wave_tx_busy():
        time.sleep(0.002)
        if time.time() - t0 > 60:
            pi.wave_tx_stop()
            print("  TIMEOUT")
            break

    if cb: cb.cancel()
    pi.wave_delete(wid)
    pi.wave_clear()
    return _hit


def backoff_all():
    """Отъехать от нажатых концевиков."""
    if pi.read(SENSOR_LEFT) == 1:
        print("[INIT] LEFT нажат -> отъезд вправо")
        move(1, 1, BACKOFF, FAST)
        time.sleep(0.05)
    if pi.read(SENSOR_RIGHT) == 1:
        print("[INIT] RIGHT нажат -> отъезд влево")
        move(0, 0, BACKOFF, FAST)
        time.sleep(0.05)
    if pi.read(SENSOR_BOTTOM) == 1:
        print("[INIT] BOTTOM нажат -> отъезд вверх")
        move(1, 0, BACKOFF, FAST)
        time.sleep(0.05)
    if pi.read(SENSOR_TOP) == 1:
        print("[INIT] TOP нажат -> отъезд вниз")
        move(0, 1, BACKOFF, FAST)
        time.sleep(0.05)


def home_axis(name, fast_ad, fast_bd, back_ad, back_bd, sensor, backoff=BACKOFF):
    print(f"\n[{name}] Быстрый подход...", end=" ", flush=True)
    hit = move(fast_ad, fast_bd, 100000, FAST, sensor)
    if not hit:
        print("FAIL: концевик не найден!")
        return False
    print("концевик!")

    print(f"[{name}] Отъезд {backoff} шагов...", end=" ", flush=True)
    move(back_ad, back_bd, backoff, FAST)
    print("ок")
    time.sleep(0.1)

    print(f"[{name}] Медленное прижатие...", end=" ", flush=True)
    hit2 = move(fast_ad, fast_bd, backoff + 50, SLOW, sensor)
    if hit2:
        print("HOME OK")
        return True
    else:
        print("FAIL: концевик не сработал на медленном подходе")
        return False


def main():
    print("=" * 50)
    print("  HOMING BookCabinet v3 (pigpio DMA)")
    print(f"  FAST={FAST} SLOW={SLOW} BACKOFF={BACKOFF}")
    print("  HOME = LEFT(pin9) + BOTTOM(pin8)")
    print("=" * 50)

    print("\n[INIT] Состояние концевиков:")
    for name, pin in [("LEFT",9),("RIGHT",10),("BOTTOM",8),("TOP",11)]:
        val = pi.read(pin)
        print(f"  {name}(pin{pin}): {'НАЖАТ' if val==1 else 'свободен'}")

    backoff_all()

    ok_x = home_axis(
        name="X->LEFT",
        fast_ad=0, fast_bd=0,   # влево
        back_ad=1, back_bd=1,   # отъезд вправо
        sensor=SENSOR_LEFT
    )
    if not ok_x:
        print("\nХоминг X не удался, выход.")
        pi.stop()
        sys.exit(1)

    time.sleep(0.3)

    ok_y = home_axis(
        name="Y->BOTTOM",
        fast_ad=0, fast_bd=1,   # вниз
        back_ad=1, back_bd=0,   # отъезд вверх
        sensor=SENSOR_BOTTOM,
        backoff=500
    )

    pi.stop()

    if ok_x and ok_y:
        print("\n==> HOME OK: LEFT + BOTTOM")
    else:
        print("\n==> Хоминг завершён с ошибками")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pi.wave_tx_stop()
        pi.stop()
        print("\nПрервано")
