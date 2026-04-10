#!/usr/bin/env python3
"""
CoreXY motion v2 for BookCabinet.
- stable endstop confirmation
- smooth wave_chain movement
- precise endstop seek: fast -> backoff -> slow

Usage:
  python3 tools/corexy_motion_v2.py home
  python3 tools/corexy_motion_v2.py x-sweep
  python3 tools/corexy_motion_v2.py y-sweep
"""
import pigpio
import time
import sys

MOTOR_A_STEP = 14
MOTOR_A_DIR  = 15
MOTOR_B_STEP = 19
MOTOR_B_DIR  = 21

SENSOR_LEFT   = 9
SENSOR_RIGHT  = 10
SENSOR_BOTTOM = 8
SENSOR_TOP    = 11

FAST = 600
SLOW = 250
BACKOFF_X = 300
BACKOFF_Y = 500
WAVE_SEG = 200
STEP_MASK = (1 << MOTOR_A_STEP) | (1 << MOTOR_B_STEP)

pi = pigpio.pi()
if not pi.connected:
    sys.exit('ОШИБКА: pigpiod не запущен')

for p in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
    pi.set_mode(p, pigpio.OUTPUT)
    pi.write(p, 0)
for p in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
    pi.set_mode(p, pigpio.INPUT)
    pi.set_pull_up_down(p, pigpio.PUD_OFF)
    pi.set_glitch_filter(p, 300)


def state():
    return {
        'LEFT': pi.read(SENSOR_LEFT),
        'RIGHT': pi.read(SENSOR_RIGHT),
        'BOTTOM': pi.read(SENSOR_BOTTOM),
        'TOP': pi.read(SENSOR_TOP),
    }


def sensor_stable(pin, reads=5, delay=0.002, need=4):
    acc = 0
    for _ in range(reads):
        acc += pi.read(pin)
        time.sleep(delay)
    return acc >= need


def move(a_dir, b_dir, n, speed, stop_sensor=None):
    """Smooth repeated wave_chain motion with stable endstop stop."""
    hit = False
    pi.write(MOTOR_A_DIR, a_dir)
    pi.write(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)

    if stop_sensor is not None and sensor_stable(stop_sensor, reads=3, delay=0.001, need=2):
        return True

    def _on_endstop(gpio, level, tick):
        nonlocal hit
        if sensor_stable(stop_sensor, reads=3, delay=0.001, need=2):
            hit = True
            pi.wave_tx_stop()

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
        if cb:
            cb.cancel()
        raise RuntimeError(f'wave_create error: {wid}')

    reps = max(1, n // WAVE_SEG)
    remainder = n % WAVE_SEG

    chain = bytes([255, 0, wid, 255, 1, reps & 0xFF, (reps >> 8) & 0xFF])
    pi.wave_chain(chain)

    t0 = time.time()
    while pi.wave_tx_busy():
        time.sleep(0.002)
        if stop_sensor is not None and sensor_stable(stop_sensor, reads=3, delay=0.001, need=2):
            hit = True
            pi.wave_tx_stop()
            break
        if time.time() - t0 > 60:
            pi.wave_tx_stop()
            print('  TIMEOUT')
            break

    if remainder > 0 and not hit:
        rem_pulses = []
        for _ in range(remainder):
            rem_pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
            rem_pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
        pi.wave_clear()
        pi.wave_add_generic(rem_pulses)
        wid2 = pi.wave_create()
        if wid2 >= 0:
            pi.wave_send_once(wid2)
            t1 = time.time()
            while pi.wave_tx_busy():
                time.sleep(0.002)
                if stop_sensor is not None and sensor_stable(stop_sensor, reads=3, delay=0.001, need=2):
                    hit = True
                    pi.wave_tx_stop()
                    break
                if time.time() - t1 > 30:
                    pi.wave_tx_stop()
                    print('  TIMEOUT remainder')
                    break
            pi.wave_delete(wid2)

    if cb:
        cb.cancel()
    try:
        pi.wave_delete(wid)
    except pigpio.error:
        pass
    pi.wave_clear()
    return hit


def backoff_if_pressed(name, sensor, a_dir, b_dir, steps):
    if sensor_stable(sensor, reads=3, delay=0.001, need=2):
        print(f'[INIT] {name} pressed -> backoff {steps}')
        move(a_dir, b_dir, steps, SLOW)
        time.sleep(0.05)


def seek_axis(name, go_ad, go_bd, sensor, back_ad, back_bd, backoff):
    print(f'[{name}] FAST...', end=' ', flush=True)
    hit_fast = move(go_ad, go_bd, 100000, FAST, sensor)
    print('OK' if hit_fast else 'FAIL', state())
    if not hit_fast:
        return False

    print(f'[{name}] BACKOFF {backoff}...', end=' ', flush=True)
    move(back_ad, back_bd, backoff, SLOW)
    print('OK', state())
    time.sleep(0.05)

    print(f'[{name}] SLOW...', end=' ', flush=True)
    hit_slow = move(go_ad, go_bd, backoff + 100, SLOW, sensor)
    print('OK' if hit_slow else 'FAIL', state())
    return hit_fast and hit_slow


def home_xy():
    print('HOME start', state())
    backoff_if_pressed('LEFT', SENSOR_LEFT, 1, 1, BACKOFF_X)
    backoff_if_pressed('RIGHT', SENSOR_RIGHT, 0, 0, BACKOFF_X)
    backoff_if_pressed('BOTTOM', SENSOR_BOTTOM, 1, 0, BACKOFF_Y)
    backoff_if_pressed('TOP', SENSOR_TOP, 0, 1, BACKOFF_Y)

    ok_x = seek_axis('X->LEFT', 0, 0, SENSOR_LEFT, 1, 1, BACKOFF_X)
    if not ok_x:
        return False
    ok_y = seek_axis('Y->BOTTOM', 0, 1, SENSOR_BOTTOM, 1, 0, BACKOFF_Y)
    return ok_y


def x_sweep():
    print('X sweep start', state())
    backoff_if_pressed('LEFT', SENSOR_LEFT, 1, 1, BACKOFF_X)
    ok_r = seek_axis('X->RIGHT', 1, 1, SENSOR_RIGHT, 0, 0, BACKOFF_X)
    if not ok_r:
        return False
    backoff_if_pressed('RIGHT', SENSOR_RIGHT, 0, 0, BACKOFF_X)
    ok_l = seek_axis('X->LEFT', 0, 0, SENSOR_LEFT, 1, 1, BACKOFF_X)
    return ok_l


def y_sweep():
    print('Y sweep start', state())
    backoff_if_pressed('BOTTOM', SENSOR_BOTTOM, 1, 0, BACKOFF_Y)
    ok_t = seek_axis('Y->TOP', 1, 0, SENSOR_TOP, 0, 1, BACKOFF_Y)
    if not ok_t:
        return False
    backoff_if_pressed('TOP', SENSOR_TOP, 0, 1, BACKOFF_Y)
    ok_b = seek_axis('Y->BOTTOM', 0, 1, SENSOR_BOTTOM, 1, 0, BACKOFF_Y)
    return ok_b


if __name__ == '__main__':
    try:
        cmd = sys.argv[1] if len(sys.argv) > 1 else 'home'
        if cmd == 'home':
            ok = home_xy()
        elif cmd == 'x-sweep':
            ok = x_sweep()
        elif cmd == 'y-sweep':
            ok = y_sweep()
        else:
            raise SystemExit(f'unknown command: {cmd}')
        print('FINAL', state(), 'ok=', ok)
        sys.exit(0 if ok else 1)
    finally:
        pi.wave_tx_stop()
        pi.write(MOTOR_A_STEP, 0)
        pi.write(MOTOR_B_STEP, 0)
        pi.stop()
