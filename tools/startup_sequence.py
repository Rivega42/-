#!/usr/bin/env python3
"""
BookCabinet — Startup Sequence
1. XY Homing через corexy_motion_v2 (HOME = LEFT + BOTTOM)
2. Калибровка платформы (ТОЛЬКО после хоминга!)
"""
from __future__ import annotations

import pigpio
import time

from corexy_motion_v2 import CoreXYMotionV2, MotionConfig

# Platform GPIO
TRAY_STEP = 18
TRAY_DIR = 27
TRAY_EN1 = 25
TRAY_EN2 = 26
ENDSTOP_FRONT = 7
ENDSTOP_BACK = 20
TRAY_FREQ = 12000

XY_CONFIG = MotionConfig(fast=800, slow=300, backoff_x=300, backoff_y=500)


def calibrate_tray(pi: pigpio.pi) -> tuple[bool, int, int]:
    """Calibrate tray. Returns (success, total_steps, center)."""
    
    for pin in [TRAY_STEP, TRAY_DIR, TRAY_EN1, TRAY_EN2]:
        pi.set_mode(pin, pigpio.OUTPUT)
    for pin in [ENDSTOP_FRONT, ENDSTOP_BACK]:
        pi.set_mode(pin, pigpio.INPUT)
        pi.set_pull_up_down(pin, pigpio.PUD_UP)
    
    # Enable driver
    pi.write(TRAY_EN1, 0)
    pi.write(TRAY_EN2, 0)
    
    period_us = int(1000000 / TRAY_FREQ)
    pulse_us = period_us // 2
    
    pi.wave_clear()
    waveform = [
        pigpio.pulse(1 << TRAY_STEP, 0, pulse_us),
        pigpio.pulse(0, 1 << TRAY_STEP, pulse_us)
    ]
    pi.wave_add_generic(waveform)
    wave_id = pi.wave_create()
    
    def move_until(direction, endstop_pin, max_time=15):
        pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        pi.wave_send_repeat(wave_id)
        start = time.time()
        while pi.read(endstop_pin) == 0 and (time.time() - start) < max_time:
            time.sleep(0.0005)
        pi.wave_tx_stop()
        elapsed = time.time() - start
        steps = int(elapsed * TRAY_FREQ)
        reached = pi.read(endstop_pin) == 1
        return steps, reached
    
    try:
        print('[TRAY] -> FRONT...', end=' ', flush=True)
        _, reached = move_until(0, ENDSTOP_FRONT)
        if not reached:
            print('FAIL')
            return False, 0, 0
        print('OK')
        time.sleep(0.3)
        
        print('[TRAY] -> BACK...', end=' ', flush=True)
        total_steps, reached = move_until(1, ENDSTOP_BACK)
        if not reached:
            print('FAIL')
            return False, 0, 0
        print(f'OK ({total_steps} шагов)')
        time.sleep(0.3)
        
        print('[TRAY] -> CENTER...', end=' ', flush=True)
        center = total_steps // 2
        pi.write(TRAY_DIR, 0)
        time.sleep(0.01)
        pi.wave_send_repeat(wave_id)
        time.sleep(center / TRAY_FREQ)
        pi.wave_tx_stop()
        print(f'OK ({center})')
        
        return True, total_steps, center
        
    finally:
        pi.wave_delete(wave_id)
        pi.wave_clear()
        pi.write(TRAY_EN1, 1)
        pi.write(TRAY_EN2, 1)


def main() -> int:
    print('=' * 50)
    print('  BookCabinet Startup')
    print('=' * 50)
    
    # Step 1: XY Homing
    print('\n[XY] Хоминг...')
    try:
        with CoreXYMotionV2(config=XY_CONFIG) as motion:
            for name, val in motion.state().items():
                print(f'      {name}: {"НАЖАТ" if val == 1 else "-"}')
            ok = motion.home_xy()
            if not ok:
                print('[XY] FAIL')
                return 1
            print('[XY] HOME OK')
    except Exception as e:
        print(f'[XY] ERROR: {e}')
        return 1
    
    time.sleep(0.5)
    
    # Step 2: Tray Calibration
    print('\n[TRAY] Калибровка...')
    pi = pigpio.pi()
    if not pi.connected:
        print('[TRAY] ERROR: pigpiod!')
        return 1
    
    try:
        ok, total, center = calibrate_tray(pi)
        if not ok:
            return 1
    finally:
        pi.stop()
    
    print('\n' + '=' * 50)
    print('  STARTUP OK')
    print(f'  XY: HOME | Tray: {total} steps, center={center}')
    print('=' * 50)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nПрервано')
        raise SystemExit(130)
