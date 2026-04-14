#!/usr/bin/env python3
"""
BookCabinet — Startup Sequence
Хоминг XY + Калибровка платформы

Запуск: python3 startup_sequence.py
"""

import pigpio
import time

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
XY_FREQ_FAST = 1500
XY_FREQ_SLOW = 400
TRAY_FREQ = 12000
GLITCH_FILTER_US = 300


class BookCabinet:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Cannot connect to pigpiod")
        
        self._setup_pins()
        self.tray_total_steps = 0
        self.tray_center = 0
        
    def _setup_pins(self):
        # XY motors
        for pin in [MOTOR_A_STEP, MOTOR_A_DIR, MOTOR_B_STEP, MOTOR_B_DIR]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        # XY endstops with glitch filter
        for pin in [SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
        self.pi.set_glitch_filter(SENSOR_LEFT, GLITCH_FILTER_US)
        self.pi.set_glitch_filter(SENSOR_RIGHT, GLITCH_FILTER_US)
        
        # Tray motor
        for pin in [TRAY_STEP, TRAY_DIR, TRAY_EN1, TRAY_EN2]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        # Tray endstops
        for pin in [ENDSTOP_FRONT, ENDSTOP_BACK]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
    
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
        """Move tray until endstop. Returns (steps, reached)"""
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
        """Calibrate tray: find endstops, measure travel, go to center"""
        print("[TRAY] Starting calibration...")
        
        # Enable driver
        self.pi.write(TRAY_EN1, 0)
        self.pi.write(TRAY_EN2, 0)
        
        wave_id = self._create_tray_wave()
        
        try:
            # Step 1: Move to FRONT
            print("[TRAY] Moving to FRONT...")
            steps_to_front, reached = self._tray_move_until(0, ENDSTOP_FRONT, wave_id)
            if not reached:
                print("[TRAY] ERROR: FRONT endstop not reached!")
                return False
            print(f"[TRAY] FRONT reached after {steps_to_front} steps")
            time.sleep(0.3)
            
            # Step 2: Move to BACK (count total travel)
            print("[TRAY] Moving to BACK...")
            self.tray_total_steps, reached = self._tray_move_until(1, ENDSTOP_BACK, wave_id)
            if not reached:
                print("[TRAY] ERROR: BACK endstop not reached!")
                return False
            print(f"[TRAY] BACK reached. Total travel: {self.tray_total_steps} steps")
            time.sleep(0.3)
            
            # Step 3: Move to CENTER
            print("[TRAY] Moving to CENTER...")
            self.tray_center = self.tray_total_steps // 2
            self.pi.write(TRAY_DIR, 0)
            time.sleep(0.01)
            self.pi.wave_send_repeat(wave_id)
            time.sleep(self.tray_center / TRAY_FREQ)
            self.pi.wave_tx_stop()
            print(f"[TRAY] CENTER at {self.tray_center} steps")
            
            print("[TRAY] Calibration complete!")
            return True
            
        finally:
            self.pi.wave_delete(wave_id)
            # Disable driver
            self.pi.write(TRAY_EN1, 1)
            self.pi.write(TRAY_EN2, 1)
    
    def home_xy(self):
        """Home XY carriage to LEFT + BOTTOM"""
        print("[XY] Starting homing...")
        # TODO: implement XY homing from corexy_pigpio.py
        print("[XY] Homing not implemented yet - use corexy_pigpio.py")
        return True
    
    def startup(self):
        """Full startup sequence: XY homing + Tray calibration"""
        print("="*50)
        print("BookCabinet Startup Sequence")
        print("="*50)
        print()
        
        # Step 1: Home XY
        if not self.home_xy():
            print("STARTUP FAILED: XY homing error")
            return False
        
        # Step 2: Calibrate Tray
        if not self.calibrate_tray():
            print("STARTUP FAILED: Tray calibration error")
            return False
        
        print()
        print("="*50)
        print("STARTUP COMPLETE")
        print(f"  Tray total: {self.tray_total_steps} steps")
        print(f"  Tray center: {self.tray_center} steps")
        print("="*50)
        return True
    
    def close(self):
        self.pi.stop()


if __name__ == "__main__":
    cabinet = BookCabinet()
    try:
        cabinet.startup()
    finally:
        cabinet.close()
