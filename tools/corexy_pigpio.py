#!/usr/bin/env python3
"""
CoreXY движение через pigpio — аппаратная генерация импульсов через DMA.
Скорость ровная без дёрганий.
"""
import pigpio
import time
import sys

# === Пины ===
MOTOR_A_STEP = 14
MOTOR_A_DIR  = 15
MOTOR_B_STEP = 19
MOTOR_B_DIR  = 21

SENSOR_LEFT   = 9
SENSOR_RIGHT  = 10
SENSOR_BOTTOM = 8
SENSOR_TOP    = 11

# === Параметры ===
FAST = 1500   # шагов/сек
SLOW = 400     # шагов/сек (хоминг медленная фаза)
BACK = 200     # шагов отъезда
CHUNK = 200    # шагов на одну волну

pi = pigpio.pi()
if not pi.connected:
    print("ОШИБКА: pigpiod не запущен! sudo pigpiod")
    sys.exit(1)

# Настройка пинов
for p in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
    pi.set_mode(p, pigpio.OUTPUT)
    pi.write(p, 0)
for p in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
    pi.set_mode(p, pigpio.INPUT)
    pi.set_pull_up_down(p, pigpio.PUD_UP)

# Маски пинов
STEP_MASK = (1 << MOTOR_A_STEP) | (1 << MOTOR_B_STEP)


def make_wave(n, half_us):
    """Создать волну из n шагов с периодом half_us мкс."""
    pulses = []
    for _ in range(n):
        pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
        pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
    pi.wave_clear()
    pi.wave_add_generic(pulses)
    return pi.wave_create()


def step_pigpio(a_dir, b_dir, n, speed, stop_sensor=None):
    """
    Выполнить n шагов через DMA.
    Возвращает кол-во пройденных шагов.
    """
    pi.write(MOTOR_A_DIR, a_dir)
    pi.write(MOTOR_B_DIR, b_dir)
    time.sleep(0.001)  # DIR settle

    half_us = int(1_000_000 / (2 * speed))
    wid = make_wave(CHUNK, half_us)

    done = 0
    while done < n:
        # Проверяем датчик перед каждым чанком
        if stop_sensor is not None and pi.read(stop_sensor):
            break

        remaining = n - done
        if remaining < CHUNK:
            pi.wave_delete(wid)
            wid = make_wave(remaining, half_us)

        pi.wave_send_once(wid)
        while pi.wave_tx_busy():
            time.sleep(0.0001)
        done += min(CHUNK, remaining)

    pi.wave_delete(wid)
    return done


def go(name, ad, bd, sensor, back_ad, back_bd):
    print(f"  {name}...", end=" ", flush=True)
    n = step_pigpio(ad, bd, 100000, FAST, sensor)
    print(f"концевик на шаге {n}")
    step_pigpio(back_ad, back_bd, BACK, FAST)
    time.sleep(0.1)


def home_axis(name, ad, bd, sensor, back_ad, back_bd):
    print(f"  {name}...", end=" ", flush=True)
    step_pigpio(ad, bd, 100000, FAST, sensor)
    step_pigpio(back_ad, back_bd, BACK, FAST)
    time.sleep(0.1)
    n2 = step_pigpio(ad, bd, BACK + 50, SLOW, sensor)
    print(f"HOME шаг {n2}")


def main():
    print("=" * 50)
    print(f"  ОБХОД КОНЦЕВИКОВ (pigpio DMA, {FAST} шагов/сек)")
    print("=" * 50)

    go("X→LEFT",   0, 0, SENSOR_LEFT,   1, 1)
    go("Y→TOP",    1, 0, SENSOR_TOP,    0, 1)
    go("X→RIGHT",  1, 1, SENSOR_RIGHT,  0, 0)
    go("Y→BOTTOM", 0, 1, SENSOR_BOTTOM, 1, 0)

    time.sleep(0.3)
    print("\nХоминг:")
    home_axis("X→RIGHT",  1, 1, SENSOR_RIGHT,  0, 0)
    time.sleep(0.3)
    home_axis("Y→BOTTOM", 0, 1, SENSOR_BOTTOM, 1, 0)

    pi.stop()
    print("\n✓ HOME (RIGHT+BOTTOM)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pi.stop()
        print("\nПрервано")
