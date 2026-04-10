#!/usr/bin/env python3
"""Дебаг хоминга X — glitch=500us."""
import pigpio
import time
import sys
import threading

sys.path.insert(0, "/home/admin42/bookcabinet")
from bookcabinet.config import GPIO_PINS

pi = pigpio.pi()

PIN_X = GPIO_PINS["SENSOR_X_END"]
PIN_A_STEP = GPIO_PINS["MOTOR_A_STEP"]
PIN_A_DIR = GPIO_PINS["MOTOR_A_DIR"]
PIN_B_STEP = GPIO_PINS["MOTOR_B_STEP"]
PIN_B_DIR = GPIO_PINS["MOTOR_B_DIR"]

FAST_SPEED = 1000
SLOW_SPEED = 300
BACKOFF = 500
sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

samples = []
sampling = False
def sampler():
    while sampling:
        samples.append((time.time(), pi.read(PIN_X)))
        time.sleep(0.0005)

def pct(t_start, t_end):
    s = [x for x in samples if t_start <= x[0] <= t_end]
    if not s: return 0.0, 0
    h = sum(1 for x in s if x[1] == 1)
    return (h / len(s)) * 100, len(s)

sampling = True
threading.Thread(target=sampler, daemon=True).start()

GLITCH = 500  # <-- фильтр 500us

print(f"=== X homing debug (glitch={GLITCH}us) ===")
print(f"Pin X: {PIN_X}, текущее: {pi.read(PIN_X)}")
print()

# 1. Отъезд
print("1. LEFT 8000...", flush=True)
pi.write(PIN_A_DIR, 0); pi.write(PIN_B_DIR, 0); time.sleep(0.001)
pus = int(500000 / FAST_SPEED)
done = 0
while done < 8000:
    n = min(2000, 8000 - done)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus))
        wf.append(pigpio.pulse(0, sm, pus))
    pi.wave_clear(); pi.wave_add_generic(wf)
    wid = pi.wave_create(); pi.wave_send_once(wid)
    while pi.wave_tx_busy(): time.sleep(0.001)
    pi.wave_delete(wid); done += n
time.sleep(0.3)
print(f"   X pin = {pi.read(PIN_X)}")
print()

# 2. Быстрая
print("2. БЫСТРАЯ: RIGHT (glitch=500us)...", flush=True)
pi.set_glitch_filter(PIN_X, GLITCH)
time.sleep(0.01)

hit = [False]
def on_hit(gpio, level, tick):
    if level == 1:
        pi.wave_tx_stop()
        hit[0] = True
cb = pi.callback(PIN_X, pigpio.RISING_EDGE, on_hit)

pi.write(PIN_A_DIR, 1); pi.write(PIN_B_DIR, 1); time.sleep(0.001)
done = 0; t0 = time.time()
while done < 80000 and not hit[0]:
    n = min(2000, 80000 - done)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus))
        wf.append(pigpio.pulse(0, sm, pus))
    pi.wave_clear(); pi.wave_add_generic(wf)
    wid = pi.wave_create(); pi.wave_send_once(wid)
    while pi.wave_tx_busy(): time.sleep(0.001)
    pi.wave_delete(wid); done += n
cb.cancel()
pi.set_glitch_filter(PIN_X, 0)
dt = time.time() - t0
p, n = pct(t0, time.time())
print(f"   HIT={hit[0]}, шагов≈{done}, время={dt:.2f}с")
print(f"   X HIGH={p:.1f}% ({n} samples)")

time.sleep(0.2)
t0 = time.time(); time.sleep(0.3)
p, n = pct(t0, time.time())
print(f"   Покой: X HIGH={p:.1f}%")
print()

# 3. Backoff
print(f"3. BACKOFF: LEFT {BACKOFF}...", flush=True)
pi.write(PIN_A_DIR, 0); pi.write(PIN_B_DIR, 0); time.sleep(0.001)
done = 0
while done < BACKOFF:
    n = min(500, BACKOFF - done)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus))
        wf.append(pigpio.pulse(0, sm, pus))
    pi.wave_clear(); pi.wave_add_generic(wf)
    wid = pi.wave_create(); pi.wave_send_once(wid)
    while pi.wave_tx_busy(): time.sleep(0.001)
    pi.wave_delete(wid); done += n
time.sleep(0.2)
print(f"   X pin = {pi.read(PIN_X)}")
print()

# 4. Медленная
print("4. МЕДЛЕННАЯ: RIGHT (glitch=500us)...", flush=True)
pi.set_glitch_filter(PIN_X, GLITCH)
time.sleep(0.01)

hit2 = [False]
def on_hit2(gpio, level, tick):
    if level == 1:
        pi.wave_tx_stop()
        hit2[0] = True
cb2 = pi.callback(PIN_X, pigpio.RISING_EDGE, on_hit2)

pi.write(PIN_A_DIR, 1); pi.write(PIN_B_DIR, 1); time.sleep(0.001)
pus2 = int(500000 / SLOW_SPEED)
done2 = 0; t0 = time.time()
MAX2 = BACKOFF + 500
while done2 < MAX2 and not hit2[0]:
    n = min(500, MAX2 - done2)
    wf = []
    for _ in range(n):
        wf.append(pigpio.pulse(sm, 0, pus2))
        wf.append(pigpio.pulse(0, sm, pus2))
    pi.wave_clear(); pi.wave_add_generic(wf)
    wid = pi.wave_create(); pi.wave_send_once(wid)
    while pi.wave_tx_busy(): time.sleep(0.001)
    pi.wave_delete(wid); done2 += n
cb2.cancel()
pi.set_glitch_filter(PIN_X, 0)
dt = time.time() - t0
p, n = pct(t0, time.time())
print(f"   HIT={hit2[0]}, шагов≈{done2}, время={dt:.2f}с")
print(f"   X HIGH={p:.1f}% ({n} samples)")

sampling = False
print()
print("=== ГОТОВО ===")
pi.stop()
