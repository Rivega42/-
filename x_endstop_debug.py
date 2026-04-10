#!/usr/bin/env python3
"""Дебаг X концевика: логируем % HIGH/LOW за интервалы + двигаем каретку."""
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

# Сэмплирование пина в отдельном потоке
samples = []
sampling = False

def sampler():
    while sampling:
        samples.append((time.time(), pi.read(PIN_X)))
        time.sleep(0.001)  # 1000 замеров/сек

def get_percent(start_time, end_time):
    """Процент HIGH за период."""
    relevant = [s for s in samples if start_time <= s[0] <= end_time]
    if not relevant:
        return 0.0, 0
    highs = sum(1 for s in relevant if s[1] == 1)
    return (highs / len(relevant)) * 100, len(relevant)

def move_xy(direction, steps, speed=1000):
    if direction == "right":
        a_dir, b_dir = 1, 1
    else:
        a_dir, b_dir = 0, 0
    
    pi.write(PIN_A_DIR, a_dir)
    pi.write(PIN_B_DIR, b_dir)
    time.sleep(0.001)
    
    sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)
    pus = int(500000 / speed)
    
    done = 0
    while done < steps:
        n = min(1000, steps - done)
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

print(f"=== X endstop debug (%) ===")
print(f"Pin: {PIN_X}, текущее: {pi.read(PIN_X)}")
print(f"Сэмплирование 1000 Гц")
print()

# Запускаем сэмплер
sampling = True
t = threading.Thread(target=sampler, daemon=True)
t.start()

time.sleep(0.2)  # baseline

for i in range(2):
    print(f"--- Цикл {i+1} ---")
    
    # Тишина
    t0 = time.time()
    time.sleep(0.3)
    pct, n = get_percent(t0, time.time())
    print(f"  Покой:       HIGH={pct:5.1f}%  ({n} samples)")
    
    # LEFT
    t0 = time.time()
    move_xy("left", 5000)
    pct, n = get_percent(t0, time.time())
    print(f"  LEFT 5000:   HIGH={pct:5.1f}%  ({n} samples)")
    time.sleep(0.2)
    
    # Тишина после LEFT
    t0 = time.time()
    time.sleep(0.3)
    pct, n = get_percent(t0, time.time())
    print(f"  Покой:       HIGH={pct:5.1f}%  ({n} samples)")
    
    # RIGHT
    t0 = time.time()
    move_xy("right", 5000)
    pct, n = get_percent(t0, time.time())
    print(f"  RIGHT 5000:  HIGH={pct:5.1f}%  ({n} samples)")
    time.sleep(0.2)
    
    # Тишина после RIGHT
    t0 = time.time()
    time.sleep(0.3)
    pct, n = get_percent(t0, time.time())
    print(f"  Покой:       HIGH={pct:5.1f}%  ({n} samples)")
    
    print()

sampling = False
time.sleep(0.1)

print(f"Финал: pi.read(X) = {pi.read(PIN_X)}")
print(f"Всего samples: {len(samples)}")
pi.stop()
