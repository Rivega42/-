#!/usr/bin/env python3
"""
BookCabinet — Startup Sequence

1. XY Homing через corexy_motion_v2 (HOME = LEFT + BOTTOM)
2. Калибровка платформы через tray_platform (ТОЛЬКО после хоминга!)

Запуск: python3 startup_sequence.py
"""
from __future__ import annotations

import time
import sys

from corexy_motion_v2 import CoreXYMotionV2, MotionConfig
from tray_platform import TrayPlatform

# XY Homing config
XY_CONFIG = MotionConfig(fast=800, slow=300, backoff_x=300, backoff_y=500)


def main() -> int:
    print("=" * 50)
    print("  BookCabinet Startup")
    print("=" * 50)
    
    # Step 1: XY Homing
    print("\n[XY] Homing...")
    try:
        with CoreXYMotionV2(config=XY_CONFIG) as motion:
            for name, val in motion.state().items():
                status = "PRESSED" if val == 1 else "-"
                print(f"      {name}: {status}")
            ok = motion.home_xy()
            if not ok:
                print("[XY] FAIL")
                return 1
            print("[XY] HOME OK")
    except Exception as e:
        print(f"[XY] ERROR: {e}")
        return 1
    
    time.sleep(0.5)
    
    # Step 2: Tray Calibration (only after XY homing!)
    print("\n[TRAY] Calibration...")
    tray = TrayPlatform()
    try:
        ok = tray.calibrate()
        if not ok:
            print("[TRAY] FAIL")
            return 1
    finally:
        tray.close()
    
    print("\n" + "=" * 50)
    print("  STARTUP OK")
    print(f"  XY: HOME | Tray: {tray.total_steps} steps, center={tray.center_steps}")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
