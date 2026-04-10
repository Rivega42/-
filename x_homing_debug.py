#!/usr/bin/env python3
"""Дебаг хоминга X с подробным логом каждого шага."""
import pigpio
import time
import sys
import threading

sys.path.insert(0, "/home/admin42/bookcabinet")
from bookcabinet.config import GPIO_PINS

pi = pigpio.pi()

PIN_X = GPIO_PINS["SENSOR_X_END"]  # 10
PIN_A_STEP = GPIO_PINS["MOTOR_A_STEP"]
PIN_A_DIR = GPIO_PINS["MOTOR_A_DIR"]
PIN_B_STEP = GPIO_PINS["MOTOR_B_STEP"]
PIN_B_DIR = GPIO_PINS["MOTOR_B_DIR"]

FAST_SPEED = 1000
SLOW_SPEED = 300
BACKOFF = 500

# Логируем все события на X пине
events = []
def on_x(gpio, level, tick):
    events.append((time.time(), level))
    state = "HIGH" if level == 1 else "LOW"
    print(f"    [X EVENT] → {state}", flush=True)

cb = pi.callback(PIN_X, pigpio.EITHER_EDGE, on_x)

def wave_steps(a_dir, b_dir, steps, speed):
    pi.write(PIN_A_DIR, a_dir)
    pi.write(PIN_B_DIR, b_dir)
    time.sleep(0.001)
    sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)
    pus = int(500000 / speed)
    done = 0
    while done < steps:
        n = min(2000, steps - done)
        wf = []
        for _ in range(n):
            wf.append(pigpio.pulse(sm, 0, pus))
            wf.append(pigpio.pulse(0, sm, pus))
        pi.wave_clear()
        pi.wave_add_generic(wf)
        wid = pi.wave_create()
        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.001)
        pi.wave_delete(wid)
        done += n

print("=== X homing debug ===")
print(f"Pin X: {PIN_X}, текущее: {pi.read(PIN_X)}")
print()

# Сначала отъедем от концевика
print("1. Отъезд LEFT 5000...", flush=True)
wave_steps(0, 0, 5000, FAST_SPEED)
time.sleep(0.3)
print(f"   X pin = {pi.read(PIN_X)}")
print()

# Быстрая фаза — едем к концевику (RIGHT = a=1,b=1)
print("2. БЫСТРАЯ ФАЗА: RIGHT к концевику...", flush=True)
events.clear()
t0 = time.time()

# Callback для стопа
hit_fast = [False]
def stop_fast(gpio, level, tick):
    if level == 1:
        pi.wave_tx_stop()
        hit_fast[0] = True
cb_stop = pi.callback(PIN_X, pigpio.RISING_EDGE, stop_fast)

pi.write(PIN_A_DIR, 1)
pi.write(PIN_B_DIR, 1)
time.sleep(0.001)
sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)
pus = int(500000 / FAST_SPEED)
done = 0
MAX = 80000
while done < MAX and not hit_fast[0]:
    n = min(2000, MAX - done)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus))
        wf.append(pigpio.pulse(0, sm, pus))
    pi.wave_clear()
    pi.wave_add_generic(wf)
    wid = pi.wave_create()
    pi.wave_send_once(wid)
    while pi.wave_tx_busy():
        time.sleep(0.001)
    pi.wave_delete(wid)
    done += n

cb_stop.cancel()
dt = time.time() - t0
print(f"   HIT={hit_fast[0]}, шагов≈{done}, время={dt:.2f}с, pin={pi.read(PIN_X)}")
print(f"   Событий на X: {len(events)}")
print()

# Backoff
print(f"3. BACKOFF: LEFT {BACKOFF}...", flush=True)
events.clear()
wave_steps(0, 0, BACKOFF, FAST_SPEED)
time.sleep(0.1)
print(f"   X pin после backoff = {pi.read(PIN_X)}")
print(f"   Событий: {len(events)}")
print()

# Медленная фаза
print("4. МЕДЛЕННАЯ ФАЗА: RIGHT к концевику, speed=300...", flush=True)
events.clear()
t0 = time.time()

hit_slow = [False]
def stop_slow(gpio, level, tick):
    if level == 1:
        pi.wave_tx_stop()
        hit_slow[0] = True
cb_stop2 = pi.callback(PIN_X, pigpio.RISING_EDGE, stop_slow)

pi.write(PIN_A_DIR, 1)
pi.write(PIN_B_DIR, 1)
time.sleep(0.001)
pus_slow = int(500000 / SLOW_SPEED)
done2 = 0
MAX2 = BACKOFF + 500
while done2 < MAX2 and not hit_slow[0]:
    n = min(500, MAX2 - done2)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus_slow))
        wf.append(pigpio.pulse(0, sm, pus_slow))
    pi.wave_clear()
    pi.wave_add_generic(wf)
    wid = pi.wave_create()
    pi.wave_send_once(wid)
    while pi.wave_tx_busy():
        time.sleep(0.001)
    pi.wave_delete(wid)
    done2 += n

cb_stop2.cancel()
dt = time.time() - t0
print(f"   HIT={hit_slow[0]}, шагов≈{done2}, время={dt:.2f}с, pin={pi.read(PIN_X)}")
print(f"   Событий на X: {len(events)}")

print()
print("=== ГОТОВО ===")
cb.cancel()
pi.stop()
