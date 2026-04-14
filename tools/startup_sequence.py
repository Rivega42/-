#!/usr/bin/env python3
"""
BookCabinet — Startup Sequence
1. XY Homing (каретка в LEFT + BOTTOM)
2. Калибровка платформы (ТОЛЬКО после хоминга!)

Запуск: python3 startup_sequence.py
"""

import pigpio
import time
import sys

# === GPIO PINS ===

# XY Motors (CoreXY)
MOTOR_A_STEP = 14
MOTOR_A_DIR = 15
MOTOR_B_STEP = 19
MOTOR_B_DIR = 21

# XY Endstops
SENSOR_LEFT = 9
SENSOR_RIGHT = 10
SENSOR_BOTTOM = 8
SENSOR_TOP = 11

# Platform (Tray)
TRAY_STEP = 18
TRAY_DIR = 27
TRAY_EN1 = 25
TRAY_EN2 = 26
ENDSTOP_FRONT = 7
ENDSTOP_BACK = 20

# === SETTINGS ===
XY_FAST = 1500
XY_SLOW = 400
XY_BACK = 200
XY_WAVE_SEG = 200
GLITCH_US = 300

TRAY_FREQ = 12000

# CoreXY direction mapping
DIR_TO_SENSOR = {
    (0, 1): SENSOR_BOTTOM,
    (1, 0): SENSOR_TOP,
    (1, 1): SENSOR_RIGHT,
    (0, 0): SENSOR_LEFT,
}

STEP_MASK_XY = (1 << MOTOR_A_STEP) | (1 << MOTOR_B_STEP)


class BookCabinet:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Cannot connect to pigpiod")
        
        self._setup_pins()
        self.tray_total_steps = 0
        self.tray_center = 0
        self._xy_hit = False
        self._homed = False
        
    def _setup_pins(self):
        # XY motors
        for pin in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.write(pin, 0)
        
        # XY endstops with glitch filter
        for pin in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
            self.pi.set_glitch_filter(pin, GLITCH_US)
        
        # Tray motor
        for pin in [TRAY_STEP, TRAY_DIR, TRAY_EN1, TRAY_EN2]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        self.pi.write(TRAY_EN1, 1)  # disabled
        self.pi.write(TRAY_EN2, 1)
        
        # Tray endstops
        for pin in [ENDSTOP_FRONT, ENDSTOP_BACK]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)

    # === XY HOMING ===
    
    def _xy_on_endstop(self, gpio, level, tick):
        if not self._xy_hit:
            self._xy_hit = True
            self.pi.wave_tx_stop()
    
    def _xy_step(self, a_dir, b_dir, n, speed, stop_sensor=None):
        self._xy_hit = False
        
        # Block if moving toward pressed endstop
        block_sensor = DIR_TO_SENSOR.get((a_dir, b_dir))
        if block_sensor and self.pi.read(block_sensor) == 1:
            return False
        
        self.pi.write(MOTOR_A_DIR, a_dir)
        self.pi.write(MOTOR_B_DIR, b_dir)
        time.sleep(0.001)
        
        cb = None
        if stop_sensor:
            cb = self.pi.callback(stop_sensor, pigpio.RISING_EDGE, self._xy_on_endstop)
        
        half_us = int(1_000_000 / (2 * speed))
        pulses = []
        seg = min(n, XY_WAVE_SEG)
        for _ in range(seg):
            pulses.append(pigpio.pulse(STEP_MASK_XY, 0, half_us))
            pulses.append(pigpio.pulse(0, STEP_MASK_XY, half_us))
        
        self.pi.wave_clear()
        self.pi.wave_add_generic(pulses)
        wid = self.pi.wave_create()
        if wid < 0:
            if cb: cb.cancel()
            return False
        
        full_reps = max(1, n // seg)
        chain = bytes([255, 0, wid, 255, 1, full_reps & 0xFF, (full_reps >> 8) & 0xFF])
        self.pi.wave_chain(chain)
        
        t0 = time.time()
        while self.pi.wave_tx_busy():
            time.sleep(0.002)
            if self._xy_hit or time.time() - t0 > 60:
                self.pi.wave_tx_stop()
                break
        
        if cb: cb.cancel()
        try: self.pi.wave_delete(wid)
        except: pass
        self.pi.wave_clear()
        
        return self._xy_hit
    
    def _home_axis(self, name, ad, bd, sensor, back_ad, back_bd):
        print(f"  {name}...", end=" ", flush=True)
        
        # Fast approach
        self._xy_step(ad, bd, 100000, XY_FAST, sensor)
        # Back off
        self._xy_step(back_ad, back_bd, XY_BACK, XY_FAST)
        time.sleep(0.1)
        # Slow approach
        hit = self._xy_step(ad, bd, XY_BACK + 50, XY_SLOW, sensor)
        
        if hit:
            print("OK")
            return True
        else:
            print("FAIL")
            return False
    
    def home_xy(self):
        print("[XY] Homing to LEFT + BOTTOM...")
        
        # Home X to LEFT
        x_ok = self._home_axis("X->LEFT", 0, 0, SENSOR_LEFT, 1, 1)
        if not x_ok:
            print("[XY] ERROR: X homing failed!")
            return False
        
        time.sleep(0.2)
        
        # Home Y to BOTTOM
        y_ok = self._home_axis("Y->BOTTOM", 0, 1, SENSOR_BOTTOM, 1, 0)
        if not y_ok:
            print("[XY] ERROR: Y homing failed!")
            return False
        
        print("[XY] Homing complete - at (0,0)")
        self._homed = True
        return True

    # === TRAY CALIBRATION ===
    
    def _create_tray_wave(self):
        period_us = int(1000000 / TRAY_FREQ)
        pulse_us = period_us // 2
        
        self.pi.wave_clear()
        waveform = [
            pigpio.pulse(1 << TRAY_STEP, 0, pulse_us),
            pigpio.pulse(0, 1 << TRAY_STEP, pulse_us)
        ]
        self.pi.wave_add_generic(waveform)
        return self.pi.wave_create()
    
    def _tray_move_until(self, direction, endstop_pin, wave_id, max_time=15):
        self.pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        
        self.pi.wave_send_repeat(wave_id)
        
        start = time.time()
        while self.pi.read(endstop_pin) == 0 and (time.time() - start) < max_time:
            time.sleep(0.0005)
        
        self.pi.wave_tx_stop()
        elapsed = time.time() - start
        steps = int(elapsed * TRAY_FREQ)
        reached = self.pi.read(endstop_pin) == 1
        return steps, reached
    
    def calibrate_tray(self):
        # SAFETY: Only calibrate if XY is homed!
        if not self._homed:
            print("[TRAY] ERROR: XY must be homed first!")
            return False
        
        print("[TRAY] Starting calibration...")
        
        self.pi.write(TRAY_EN1, 0)
        self.pi.write(TRAY_EN2, 0)
        
        wave_id = self._create_tray_wave()
        
        try:
            print("[TRAY] Moving to FRONT...")
            steps_to_front, reached = self._tray_move_until(0, ENDSTOP_FRONT, wave_id)
            if not reached:
                print("[TRAY] ERROR: FRONT not reached!")
                return False
            print(f"[TRAY] FRONT OK ({steps_to_front} steps)")
            time.sleep(0.3)
            
            print("[TRAY] Moving to BACK...")
            self.tray_total_steps, reached = self._tray_move_until(1, ENDSTOP_BACK, wave_id)
            if not reached:
                print("[TRAY] ERROR: BACK not reached!")
                return False
            print(f"[TRAY] BACK OK (total: {self.tray_total_steps} steps)")
            time.sleep(0.3)
            
            print("[TRAY] Moving to CENTER...")
            self.tray_center = self.tray_total_steps // 2
            self.pi.write(TRAY_DIR, 0)
            time.sleep(0.01)
            self.pi.wave_send_repeat(wave_id)
            time.sleep(self.tray_center / TRAY_FREQ)
            self.pi.wave_tx_stop()
            print(f"[TRAY] CENTER OK ({self.tray_center} steps)")
            
            print("[TRAY] Calibration complete!")
            return True
            
        finally:
            self.pi.wave_delete(wave_id)
            self.pi.write(TRAY_EN1, 1)
            self.pi.write(TRAY_EN2, 1)
    
    # === STARTUP ===
    
    def startup(self):
        print("=" * 50)
        print("  BookCabinet Startup Sequence")
        print("=" * 50)
        print()
        
        # Step 1: XY Homing
        if not self.home_xy():
            print("\nSTARTUP FAILED: XY homing error")
            return False
        
        time.sleep(0.5)
        
        # Step 2: Tray Calibration (only after homing!)
        if not self.calibrate_tray():
            print("\nSTARTUP FAILED: Tray calibration error")
            return False
        
        print()
        print("=" * 50)
        print("  STARTUP COMPLETE")
        print(f"  XY: HOME (0,0)")
        print(f"  Tray: {self.tray_total_steps} steps, center={self.tray_center}")
        print("=" * 50)
        return True
    
    def close(self):
        self.pi.stop()


if __name__ == "__main__":
    cabinet = BookCabinet()
    try:
        cabinet.startup()
    except KeyboardInterrupt:
        print("\nПрервано")
        cabinet.pi.wave_tx_stop()
    finally:
        cabinet.close()
