#!/usr/bin/env python3
"""
BookCabinet — Startup Calibration

Последовательность калибровки при старте шкафа:
1. Замки в нулевую позицию (500μs pulse)
2. XY homing (LEFT + BOTTOM)
3. Tray calibration (FRONT → BACK → CENTER)

Запуск: python3 startup_calibration.py

Требует: pigpiod запущен
"""
from __future__ import annotations

import time
import sys

try:
    import pigpio
except ImportError:
    print("ERROR: pigpio not installed")
    sys.exit(1)

# Locks
LOCK_FRONT = 12
LOCK_REAR = 13
LOCK_NEUTRAL_PW = 500  # pulse width μs — нейтральная позиция


def reset_locks(pi: pigpio.pi) -> None:
    """Оба замка в нейтральную позицию (0°)."""
    print("[LOCKS] Resetting to neutral (500μs)...")
    for pin in [LOCK_FRONT, LOCK_REAR]:
        pi.set_servo_pulsewidth(pin, LOCK_NEUTRAL_PW)
    time.sleep(0.5)
    # Отключить PWM после установки
    for pin in [LOCK_FRONT, LOCK_REAR]:
        pi.set_servo_pulsewidth(pin, 0)
    print("[LOCKS] OK")


def home_xy(pi: pigpio.pi) -> bool:
    """XY homing через corexy_motion_v2."""
    print("\n[XY] Homing (LEFT + BOTTOM)...")
    try:
        from corexy_motion_v2 import CoreXYMotionV2, MotionConfig
        config = MotionConfig(fast=800, homing_fast=1800, slow=300, backoff_x=300, backoff_y=500)
        motion = CoreXYMotionV2(pi=pi, config=config)
        for name, val in motion.state().items():
            print(f"  {name}: {'PRESSED' if val else '-'}")
        ok = motion.home_xy()
        print(f"[XY] {'OK' if ok else 'FAIL'}")
        return ok
    except Exception as e:
        print(f"[XY] ERROR: {e}")
        return False


def calibrate_tray(pi: pigpio.pi) -> bool:
    """Tray calibration: FRONT → BACK → CENTER."""
    print("\n[TRAY] Calibration...")
    try:
        from tray_platform import TrayPlatform
        tray = TrayPlatform()
        # TrayPlatform creates its own pi — we can't share easily
        # but that's fine for calibration
        try:
            ok = tray.calibrate()
            if ok:
                print(f"[TRAY] OK — total={tray.total_steps}, center={tray.center_steps}")
            else:
                print("[TRAY] FAIL")
            return ok
        finally:
            tray.close()
    except Exception as e:
        print(f"[TRAY] ERROR: {e}")
        return False


def main() -> int:
    print("=" * 50)
    print("  BookCabinet Startup Calibration")
    print("=" * 50)

    pi = pigpio.pi()
    if not pi.connected:
        print("ERROR: pigpiod not running")
        return 1

    try:
        # Step 1: Reset locks
        reset_locks(pi)

        # Step 2: XY Homing
        if not home_xy(pi):
            print("\nFAILED at XY homing")
            return 1

        time.sleep(0.5)

        # Step 3: Tray calibration
        if not calibrate_tray(pi):
            print("\nFAILED at tray calibration")
            return 1

        print("\n" + "=" * 50)
        print("  STARTUP CALIBRATION OK")
        print("=" * 50)
        return 0

    finally:
        pi.stop()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
