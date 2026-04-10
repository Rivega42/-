#!/usr/bin/env python3
"""Тест только медленной фазы Y — отладка."""
import pigpio, time, sys

MOTOR_A_STEP = 14; MOTOR_A_DIR = 15
MOTOR_B_STEP = 19; MOTOR_B_DIR = 21
SENSOR_BOTTOM = 8
STEP_MASK = (1 << 14) | (1 << 19)

pi = pigpio.pi()
for p in [14,15,19,21]:
    pi.set_mode(p, pigpio.OUTPUT); pi.write(p, 0)
pi.set_mode(8, pigpio.INPUT)
pi.set_pull_up_down(8, pigpio.PUD_UP)

hit = False
def on_hit(gpio, level, tick):
    global hit
    if not hit:
        hit = True
        pi.wave_tx_stop()
        print(f"  >> СТОП pin={gpio} level={level}")

print("BOTTOM =", pi.read(8))
if pi.read(8) == 1:
    print("Уже нажат, стоп")
    pi.stop()
    sys.exit()

# Медленно к BOTTOM: a=0, b=1, speed=600
pi.write(15, 0)
pi.write(21, 1)
time.sleep(0.001)

# БЕЗ glitch filter — посмотрим поможет ли
cb = pi.callback(8, pigpio.RISING_EDGE, on_hit)

SEG = 100
half = int(1_000_000 / (2 * 600))
print(f"half_us={half}, seg={SEG}")

pulses = []
for _ in range(SEG):
    pulses.append(pigpio.pulse(STEP_MASK, 0, half))
    pulses.append(pigpio.pulse(0, STEP_MASK, half))
pi.wave_clear()
pi.wave_add_generic(pulses)
wid = pi.wave_create()

reps = 30  # 3000 шагов макс
chain = bytes([255, 0, wid, 255, 1, reps & 0xFF, 0])
print(f"chain: wid={wid}, reps={reps}, total={SEG*reps} steps")

t0 = time.time()
pi.wave_chain(chain)
while pi.wave_tx_busy():
    time.sleep(0.002)
elapsed = time.time() - t0

print(f"elapsed={elapsed:.3f}s, hit={hit}")
print(f"BOTTOM={pi.read(8)}")

cb.cancel()
pi.wave_delete(wid)
pi.wave_clear()
pi.stop()
