#!/usr/bin/env python3
"""
CoreXY motion v2 for BookCabinet.
- import-safe reusable motion layer
- stable endstop confirmation
- smooth wave_chain movement
- precise endstop seek: fast -> backoff -> slow

Usage:
  python3 tools/corexy_motion_v2.py home
  python3 tools/corexy_motion_v2.py x-sweep
  python3 tools/corexy_motion_v2.py y-sweep
"""
from __future__ import annotations

from dataclasses import dataclass
import sys
import math
import time

import pigpio

MOTOR_A_STEP = 14
MOTOR_A_DIR = 15
MOTOR_B_STEP = 19
MOTOR_B_DIR = 21

SENSOR_LEFT = 9
SENSOR_RIGHT = 10
SENSOR_BOTTOM = 8
SENSOR_TOP = 11

STEP_PINS = (MOTOR_A_STEP, MOTOR_B_STEP)
DIR_PINS = (MOTOR_A_DIR, MOTOR_B_DIR)
SENSOR_PINS = (SENSOR_LEFT, SENSOR_RIGHT, SENSOR_BOTTOM, SENSOR_TOP)
STEP_MASK = (1 << MOTOR_A_STEP) | (1 << MOTOR_B_STEP)


@dataclass(frozen=True)
class MotionConfig:
    fast: int = 3000
    homing_fast: int = 1800
    slow: int = 300
    backoff_x: int = 300
    backoff_y: int = 500
    wave_seg: int = 200
    accel_steps: int = 300
    min_speed: int = 400
    glitch_us: int = 300
    stable_reads: int = 5
    stable_delay: float = 0.002
    stable_need: int = 4
    poll_reads: int = 3
    poll_delay: float = 0.001
    poll_need: int = 2
    timeout_main: float = 60.0
    timeout_remainder: float = 30.0



def _build_speed_profile(steps, v_start, v_max, accel_steps):
    if steps <= 0:
        return []
    ramp = min(accel_steps, steps // 2)
    profile = []
    for i in range(steps):
        if i < ramp:
            t = i / ramp
            v = v_start + (v_max - v_start) * (1 - math.cos(math.pi * t)) / 2
        elif i >= steps - ramp:
            t = (steps - 1 - i) / max(ramp, 1)
            v = v_start + (v_max - v_start) * (1 - math.cos(math.pi * t)) / 2
        else:
            v = v_max
        v = max(v_start, min(v_max, v))
        profile.append(int(1_000_000 / (2 * v)))
    return profile


class CoreXYMotionV2:
    def __init__(self, pi: pigpio.pi | None = None, config: MotionConfig | None = None):
        self.config = config or MotionConfig()
        self.pi = pi or pigpio.pi()
        self._owns_pi = pi is None
        if not self.pi.connected:
            raise RuntimeError('ОШИБКА: pigpiod не запущен')
        self._setup_pins()

    def _setup_pins(self) -> None:
        for pin in (*STEP_PINS, *DIR_PINS):
            self.pi.set_mode(pin, pigpio.OUTPUT)
            self.pi.write(pin, 0)
        for pin in SENSOR_PINS:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_OFF)
            self.pi.set_glitch_filter(pin, self.config.glitch_us)

    def state(self) -> dict[str, int]:
        return {
            'LEFT': self.pi.read(SENSOR_LEFT),
            'RIGHT': self.pi.read(SENSOR_RIGHT),
            'BOTTOM': self.pi.read(SENSOR_BOTTOM),
            'TOP': self.pi.read(SENSOR_TOP),
        }

    def sensor_stable(
        self,
        pin: int,
        reads: int | None = None,
        delay: float | None = None,
        need: int | None = None,
    ) -> bool:
        reads = self.config.stable_reads if reads is None else reads
        delay = self.config.stable_delay if delay is None else delay
        need = self.config.stable_need if need is None else need
        acc = 0
        for _ in range(reads):
            acc += self.pi.read(pin)
            time.sleep(delay)
        return acc >= need

    def move(self, a_dir: int, b_dir: int, steps: int, speed: int, stop_sensor: int | None = None) -> bool:
        """Smooth repeated wave_chain motion with stable endstop stop."""
        if steps <= 0:
            return False

        hit = False
        self.pi.write(MOTOR_A_DIR, a_dir)
        self.pi.write(MOTOR_B_DIR, b_dir)
        time.sleep(0.001)

        if stop_sensor is not None and self.sensor_stable(
            stop_sensor,
            reads=self.config.poll_reads,
            delay=self.config.poll_delay,
            need=self.config.poll_need,
        ):
            return True

        def _on_endstop(gpio: int, level: int, tick: int) -> None:
            nonlocal hit
            if self.sensor_stable(
                stop_sensor,
                reads=self.config.poll_reads,
                delay=self.config.poll_delay,
                need=self.config.poll_need,
            ):
                hit = True
                self.pi.wave_tx_stop()

        cb = None
        if stop_sensor is not None:
            cb = self.pi.callback(stop_sensor, pigpio.RISING_EDGE, _on_endstop)

        _profile = _build_speed_profile(steps, self.config.min_speed, speed, self.config.accel_steps)
        _pidx = 0
        seg_steps = min(self.config.wave_seg, steps)
        pulses = []
        for _si in range(seg_steps):
            _hus = _profile[_pidx] if _pidx < len(_profile) else int(1_000_000 / (2 * speed))
            _pidx += 1
            pulses.append(pigpio.pulse(STEP_MASK, 0, _hus))
            pulses.append(pigpio.pulse(0, STEP_MASK, _hus))
        self.pi.wave_clear()
        self.pi.wave_add_generic(pulses)
        wid = self.pi.wave_create()
        if wid < 0:
            if cb:
                cb.cancel()
            raise RuntimeError(f'wave_create error: {wid}')

        reps, remainder = divmod(steps, seg_steps)
        if reps > 0:
            chain = bytes([255, 0, wid, 255, 1, reps & 0xFF, (reps >> 8) & 0xFF])
            self.pi.wave_chain(chain)

            t0 = time.time()
            while self.pi.wave_tx_busy():
                time.sleep(0.002)
                if stop_sensor is not None and self.sensor_stable(
                    stop_sensor,
                    reads=self.config.poll_reads,
                    delay=self.config.poll_delay,
                    need=self.config.poll_need,
                ):
                    hit = True
                    self.pi.wave_tx_stop()
                    break
                if time.time() - t0 > self.config.timeout_main:
                    self.pi.wave_tx_stop()
                    print('  TIMEOUT')
                    break

        if remainder > 0 and not hit:
            rem_pulses = []
            for _ri in range(remainder):
                _hus = _profile[_pidx] if _pidx < len(_profile) else int(1_000_000 // (2 * speed))
                _pidx += 1
                rem_pulses.append(pigpio.pulse(STEP_MASK, 0, _hus))
                rem_pulses.append(pigpio.pulse(0, STEP_MASK, _hus))
            self.pi.wave_clear()
            self.pi.wave_add_generic(rem_pulses)
            wid2 = self.pi.wave_create()
            if wid2 >= 0:
                self.pi.wave_send_once(wid2)
                t1 = time.time()
                while self.pi.wave_tx_busy():
                    time.sleep(0.002)
                    if stop_sensor is not None and self.sensor_stable(
                        stop_sensor,
                        reads=self.config.poll_reads,
                        delay=self.config.poll_delay,
                        need=self.config.poll_need,
                    ):
                        hit = True
                        self.pi.wave_tx_stop()
                        break
                    if time.time() - t1 > self.config.timeout_remainder:
                        self.pi.wave_tx_stop()
                        print('  TIMEOUT remainder')
                        break
                try:
                    self.pi.wave_delete(wid2)
                except pigpio.error:
                    pass

        if cb:
            cb.cancel()
        try:
            self.pi.wave_delete(wid)
        except pigpio.error:
            pass
        self.pi.wave_clear()
        return hit

    def backoff_if_pressed(self, name: str, sensor: int, a_dir: int, b_dir: int, steps: int) -> None:
        if self.sensor_stable(
            sensor,
            reads=self.config.poll_reads,
            delay=self.config.poll_delay,
            need=self.config.poll_need,
        ):
            print(f'[INIT] {name} pressed -> backoff {steps}')
            self.move(a_dir, b_dir, steps, self.config.slow)
            time.sleep(0.05)

    def seek_axis(
        self,
        name: str,
        go_ad: int,
        go_bd: int,
        sensor: int,
        back_ad: int,
        back_bd: int,
        backoff: int,
        fast_steps: int = 100000,
        slow_extra: int = 100,
        opposite_sensor: int | None = None,
    ) -> bool:
        print(f'[{name}] FAST...', end=' ', flush=True)
        hit_fast = self.move(go_ad, go_bd, fast_steps, self.config.homing_fast, sensor)
        print('OK' if hit_fast else 'FAIL', self.state())
        if not hit_fast:
            return False

        print(f'[{name}] BACKOFF {backoff}...', end=' ', flush=True)
        self.move(back_ad, back_bd, backoff, self.config.slow, opposite_sensor)
        print('OK', self.state())
        time.sleep(0.05)

        # Safety check: if opposite sensor hit during backoff, abort
        if opposite_sensor is not None and self.pi.read(opposite_sensor):
            print(f'[{name}] ABORT: opposite sensor {opposite_sensor} triggered during backoff!')
            return False

        print(f'[{name}] SLOW...', end=' ', flush=True)
        hit_slow = self.move(go_ad, go_bd, backoff + slow_extra, self.config.slow, sensor)
        print('OK' if hit_slow else 'FAIL', self.state())
        return hit_fast and hit_slow

    def home_xy(self) -> bool:
        print('HOME start', self.state())
        self.backoff_if_pressed('LEFT', SENSOR_LEFT, 1, 1, self.config.backoff_x)
        self.backoff_if_pressed('RIGHT', SENSOR_RIGHT, 0, 0, self.config.backoff_x)
        self.backoff_if_pressed('BOTTOM', SENSOR_BOTTOM, 1, 0, self.config.backoff_y)
        self.backoff_if_pressed('TOP', SENSOR_TOP, 0, 1, self.config.backoff_y)

        ok_y = self.seek_axis("Y->BOTTOM", 0, 1, SENSOR_BOTTOM, 1, 0, self.config.backoff_y, opposite_sensor=SENSOR_TOP)
        if not ok_y:
            return False
        return self.seek_axis("X->LEFT", 0, 0, SENSOR_LEFT, 1, 1, self.config.backoff_x, opposite_sensor=SENSOR_RIGHT)

    def x_sweep(self) -> bool:
        print('X sweep start', self.state())
        self.backoff_if_pressed('LEFT', SENSOR_LEFT, 1, 1, self.config.backoff_x)
        ok_r = self.seek_axis('X->RIGHT', 1, 1, SENSOR_RIGHT, 0, 0, self.config.backoff_x)
        if not ok_r:
            return False
        self.backoff_if_pressed('RIGHT', SENSOR_RIGHT, 0, 0, self.config.backoff_x)
        return self.seek_axis('X->LEFT', 0, 0, SENSOR_LEFT, 1, 1, self.config.backoff_x)

    def y_sweep(self) -> bool:
        print('Y sweep start', self.state())
        self.backoff_if_pressed('BOTTOM', SENSOR_BOTTOM, 1, 0, self.config.backoff_y)
        ok_t = self.seek_axis('Y->TOP', 1, 0, SENSOR_TOP, 0, 1, self.config.backoff_y)
        if not ok_t:
            return False
        self.backoff_if_pressed('TOP', SENSOR_TOP, 0, 1, self.config.backoff_y)
        return self.seek_axis('Y->BOTTOM', 0, 1, SENSOR_BOTTOM, 1, 0, self.config.backoff_y, opposite_sensor=SENSOR_TOP)

    def stop(self) -> None:
        self.pi.wave_tx_stop()
        self.pi.write(MOTOR_A_STEP, 0)
        self.pi.write(MOTOR_B_STEP, 0)

    def close(self) -> None:
        self.stop()
        if self._owns_pi:
            self.pi.stop()

    def __enter__(self) -> 'CoreXYMotionV2':
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def run_command(cmd: str, config: MotionConfig | None = None) -> int:
    with CoreXYMotionV2(config=config) as motion:
        if cmd == 'home':
            ok = motion.home_xy()
        elif cmd == 'x-sweep':
            ok = motion.x_sweep()
        elif cmd == 'y-sweep':
            ok = motion.y_sweep()
        else:
            raise SystemExit(f'unknown command: {cmd}')
        print('FINAL', motion.state(), 'ok=', ok)
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else 'home'
    return run_command(cmd)


if __name__ == '__main__':
    raise SystemExit(main())


    def move_to(self, x: int, y: int, speed: int | None = None) -> None:
        """
        Move carriage to absolute position (x, y) from HOME using diagonal motion.
        CoreXY: diagonal = both motors, then remainder on one axis.
        
        x: steps from LEFT endstop
        y: steps from BOTTOM endstop
        """
        if speed is None:
            speed = self.config.fast

        # CoreXY directions:
        # X+ (right): A=1, B=1
        # X- (left):  A=0, B=0
        # Y+ (up):    A=1, B=0
        # Y- (down):  A=0, B=1
        # Diagonal X+Y+ (right+up): A=1,B=1 + A=1,B=0 → A dominant, but pigpio wave
        # For true diagonal: step both motors simultaneously
        # We approximate: move min(x,y) diagonally, then remainder on one axis

        diag = min(x, y)
        rem_x = x - diag
        rem_y = y - diag

        if diag > 0:
            # Move diagonally: X+ and Y+ simultaneously
            # X+: A=1,B=1 / Y+: A=1,B=0
            # Combined CoreXY diagonal X+Y+: motor_A forward (both X and Y use A=1)
            # motor_B: X needs B=1, Y needs B=0 → conflict
            # Solution: interleave X and Y steps
            # Actually for CoreXY: to move diagonally X+Y+:
            # Each step: A steps once (handles Y component), B alternates
            # Simplest: move X steps, then Y steps (already works, just sequential)
            # True simultaneous requires custom waveform — use sequential for now
            # Move X first (fast), then Y
            self.move(1, 1, diag, speed)  # diagonal component as X move
            # now at (diag, 0), need to go to (diag, diag) — move Y
            if diag > 0:
                self.move(1, 0, diag, speed)

        if rem_x > 0:
            self.move(1, 1, rem_x, speed)
        if rem_y > 0:
            self.move(1, 0, rem_y, speed)
