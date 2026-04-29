#!/usr/bin/env python3
"""
BookCabinet — Tray Platform Control

Управление платформой (лотком) шкафа.

GPIO пины (BCM):
  TRAY_STEP = 18    # Шаг мотора
  TRAY_DIR  = 27    # Направление: 0=вперёд (FRONT), 1=назад (BACK)
  TRAY_EN1  = 25    # Enable 1: LOW=работа, HIGH=отключен
  TRAY_EN2  = 26    # Enable 2: LOW=работа, HIGH=отключен

Концевики:
  ENDSTOP_FRONT = 7   # Передний: 1=нажат, 0=свободен
  ENDSTOP_BACK  = 20  # Задний: 1=нажат, 0=свободен

Параметры:
  TRAY_FREQ = 12000 Hz  # Оптимальная частота (тихо + надёжно)
  Total travel: ~21000 шагов
  Center: ~10500 шагов

Использование:
  python3 tray_platform.py calibrate  # Калибровка с backoff
  python3 tray_platform.py front      # Двигать к FRONT
  python3 tray_platform.py back       # Двигать к BACK
  python3 tray_platform.py center     # Двигать в центр
  python3 tray_platform.py status     # Состояние концевиков
"""
# IMPORTANT: These GPIO pin constants MUST match bookcabinet/config.py GPIO_PINS.
# TODO: Import from config.py to eliminate duplication (see issue #59).

import pigpio
import time
import sys

# === GPIO PINS ===
TRAY_STEP = 18
TRAY_DIR = 27
TRAY_EN1 = 25
TRAY_EN2 = 26
ENDSTOP_FRONT = 7
ENDSTOP_BACK = 20

# === PARAMETERS ===
TRAY_FREQ = 12000       # Hz - основная скорость
TRAY_FREQ_SLOW = 3000   # Hz - медленный подход
BACKOFF_STEPS = 1500    # Шагов отхода
STABLE_READS = 5        # Чтений для подтверждения концевика
STABLE_NEED = 3         # Минимум единиц для подтверждения


class TrayPlatform:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Cannot connect to pigpiod")
        
        self.total_steps = 0
        self.center_steps = 0
        self.wave_id = None
        
        self._setup_pins()
    
    def _setup_pins(self):
        for pin in [TRAY_STEP, TRAY_DIR, TRAY_EN1, TRAY_EN2]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        self.pi.write(TRAY_EN1, 1)
        self.pi.write(TRAY_EN2, 1)
        
        for pin in [ENDSTOP_FRONT, ENDSTOP_BACK]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
            self.pi.set_glitch_filter(pin, 1000)
        time.sleep(0.1)
    
    def _create_wave(self, freq):
        period_us = int(1000000 / freq)
        pulse_us = period_us // 2
        
        self.pi.wave_clear()
        waveform = [
            pigpio.pulse(1 << TRAY_STEP, 0, pulse_us),
            pigpio.pulse(0, 1 << TRAY_STEP, pulse_us)
        ]
        self.pi.wave_add_generic(waveform)
        self.wave_id = self.pi.wave_create()
        return self.wave_id
    
    def _delete_wave(self):
        if self.wave_id is not None:
            try:
                self.pi.wave_delete(self.wave_id)
            except:
                pass
            self.wave_id = None
        self.pi.wave_clear()
    
    def enable(self):
        self.pi.write(TRAY_EN1, 0)
        self.pi.write(TRAY_EN2, 0)
    
    def disable(self):
        self.pi.write(TRAY_EN1, 1)
        self.pi.write(TRAY_EN2, 1)
    
    def status(self):
        return {
            'FRONT': self.pi.read(ENDSTOP_FRONT),
            'BACK': self.pi.read(ENDSTOP_BACK),
        }
    
    def sensor_stable(self, pin):
        count = 0
        for _ in range(STABLE_READS):
            if self.pi.read(pin) == 1:
                count += 1
            time.sleep(0.001)
        return count >= STABLE_NEED
    
    def move_steps(self, direction, steps, freq=TRAY_FREQ):
        self._create_wave(freq)
        self.pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        
        self.pi.wave_send_repeat(self.wave_id)
        time.sleep(steps / freq)
        self.pi.wave_tx_stop()
        self._delete_wave()
    
    def move_until(self, direction, endstop_pin, freq=TRAY_FREQ, max_time=15.0):
        self._create_wave(freq)
        self.pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        
        self.pi.wave_send_repeat(self.wave_id)
        
        start = time.time()
        reached = False
        while (time.time() - start) < max_time:
            if self.sensor_stable(endstop_pin):
                reached = True
                break
            time.sleep(0.001)
        
        self.pi.wave_tx_stop()
        elapsed = time.time() - start
        steps = int(elapsed * freq)
        self._delete_wave()
        
        return steps, reached
    
    def home_to(self, direction, endstop_pin, name):
        print("Moving to {} (fast)...".format(name), end=" ", flush=True)
        steps, reached = self.move_until(direction, endstop_pin, TRAY_FREQ)
        if not reached:
            print("FAIL!")
            return False
        print("hit!", end=" ", flush=True)
        
        backoff_dir = 1 if direction == 0 else 0
        self.move_steps(backoff_dir, BACKOFF_STEPS, TRAY_FREQ_SLOW)
        print("backoff...", end=" ", flush=True)
        time.sleep(0.1)
        
        steps, reached = self.move_until(direction, endstop_pin, TRAY_FREQ_SLOW)
        if not reached:
            print("FAIL!")
            return False
        print("OK (slow: {} steps)".format(steps))
        return True
    
    def calibrate(self):
        print("=== TRAY CALIBRATION at {} Hz ===".format(TRAY_FREQ))
        
        self.enable()
        
        try:
            if not self.home_to(0, ENDSTOP_FRONT, "FRONT"):
                return False
            time.sleep(0.3)
            
            print("Measuring total travel...")
            print("Moving to BACK (fast)...", end=" ", flush=True)
            fast_steps, reached = self.move_until(1, ENDSTOP_BACK, TRAY_FREQ)
            if not reached:
                print("FAIL!")
                return False
            print("hit!", end=" ", flush=True)
            
            self.move_steps(0, BACKOFF_STEPS, TRAY_FREQ_SLOW)
            print("backoff...", end=" ", flush=True)
            time.sleep(0.1)
            
            slow_steps, reached = self.move_until(1, ENDSTOP_BACK, TRAY_FREQ_SLOW)
            if not reached:
                print("FAIL!")
                return False
            print("OK (slow: {} steps)".format(slow_steps))
            
            self.total_steps = fast_steps + slow_steps
            self.center_steps = self.total_steps // 2
            time.sleep(0.3)
            
            print("Moving to CENTER ({} steps)...".format(self.center_steps), end=" ", flush=True)
            self.move_steps(0, self.center_steps, TRAY_FREQ)
            print("OK")
            
            print("=== Total travel: {} steps ===".format(self.total_steps))
            return True
            
        finally:
            self._delete_wave()
            self.disable()
    
    def go_front(self):
        self.enable()
        try:
            return self.home_to(0, ENDSTOP_FRONT, "FRONT")
        finally:
            self._delete_wave()
            self.disable()
    
    def go_back(self):
        self.enable()
        try:
            return self.home_to(1, ENDSTOP_BACK, "BACK")
        finally:
            self._delete_wave()
            self.disable()
    
    def go_center(self):
        if self.total_steps == 0:
            print("ERROR: Run calibrate first!")
            return
        
        self.enable()
        try:
            if not self.home_to(0, ENDSTOP_FRONT, "FRONT"):
                return
            time.sleep(0.2)
            print("Moving to CENTER ({} steps)...".format(self.center_steps), end=" ", flush=True)
            self.move_steps(1, self.center_steps, TRAY_FREQ)
            print("OK")
        finally:
            self._delete_wave()
            self.disable()
    
    def close(self):
        self._delete_wave()
        self.disable()
        self.pi.stop()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    cmd = sys.argv[1]
    tray = TrayPlatform()
    
    try:
        if cmd == 'calibrate':
            ok = tray.calibrate()
            return 0 if ok else 1
        elif cmd == 'front':
            ok = tray.go_front()
            return 0 if ok else 1
        elif cmd == 'back':
            ok = tray.go_back()
            return 0 if ok else 1
        elif cmd == 'center':
            tray.calibrate()
            return 0
        elif cmd == 'status':
            status = tray.status()
            print("FRONT (GPIO {}): {}".format(ENDSTOP_FRONT, 'PRESSED' if status['FRONT'] else 'free'))
            print("BACK (GPIO {}): {}".format(ENDSTOP_BACK, 'PRESSED' if status['BACK'] else 'free'))
            return 0
        else:
            print("Unknown command: {}".format(cmd))
            print(__doc__)
            return 1
    finally:
        tray.close()


if __name__ == '__main__':
    sys.exit(main())
