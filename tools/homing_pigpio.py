#!/usr/bin/env python3
"""
homing_pigpio.py v4 — canonical BookCabinet homing wrapper.
HOME = LEFT + BOTTOM.
Implementation delegates to corexy_motion_v2.
"""
from __future__ import annotations

from corexy_motion_v2 import CoreXYMotionV2, MotionConfig

CONFIG = MotionConfig(
    fast=800,
    slow=300,
    backoff_x=300,
    backoff_y=500,
)


def main() -> int:
    print('=' * 50)
    print('  HOMING BookCabinet v4 (corexy_motion_v2)')
    print(
        f'  FAST={CONFIG.fast} SLOW={CONFIG.slow} '
        f'BACKOFF_X={CONFIG.backoff_x} BACKOFF_Y={CONFIG.backoff_y}'
    )
    print('  HOME = LEFT(pin9) + BOTTOM(pin8)')
    print('=' * 50)

    try:
        with CoreXYMotionV2(config=CONFIG) as motion:
            print('\n[INIT] Состояние концевиков:')
            for name, value in motion.state().items():
                print(f'  {name}: {"НАЖАТ" if value == 1 else "свободен"}')

            ok = motion.home_xy()
            if ok:
                print('\n==> HOME OK: LEFT + BOTTOM')
                return 0

            print('\n==> Хоминг завершён с ошибками')
            return 1
    except KeyboardInterrupt:
        print('\nПрервано')
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
