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
    accel_steps: int = 400
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

    def _move_at_speed(self, a_dir: int, b_dir: int, steps: int, speed: int, stop_sensor: int | None = None) -> bool:
        """Internal: move at fixed speed. Returns True if endstop hit."""
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

        half_us = int(1_000_000 / (2 * speed))
        seg_steps = min(self.config.wave_seg, steps)
        pulses = []
        for _ in range(seg_steps):
            pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
            pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
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
            for _ in range(remainder):
                rem_pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
                rem_pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
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


    def _build_accel_wave(self, steps: int, speed: int) -> int:
        """Build a SINGLE wave with variable pulse widths for smooth S-curve.

        Creates one continuous waveform where each step has its own timing.
        No gaps between segments = no jerks.

        Profile: S-curve (cosine ramp)
          - Accelerate from min_speed to speed over accel_steps
          - Cruise at speed
          - Decelerate from speed to min_speed over accel_steps

        Returns wave_id (caller must delete after use).
        Pigpio limit: ~12000 pulses per wave, so for long moves
        we chunk into wave_chain segments but each chunk is smooth.
        """
        import math

        v_min = self.config.min_speed
        v_max = max(speed, v_min)
        ramp = min(self.config.accel_steps, steps // 3)

        if ramp < 5 or v_min >= v_max:
            # Short move — single speed
            half_us = int(1_000_000 / (2 * v_max))
            pulses = []
            for _ in range(steps):
                pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
                pulses.append(pigpio.pulse(0, STEP_MASK, half_us))
            self.pi.wave_clear()
            self.pi.wave_add_generic(pulses)
            return self.pi.wave_create()

        cruise = steps - ramp * 2

        def speed_at(i: int) -> float:
            if i < ramp:
                # S-curve accel: cosine 0..pi mapped to v_min..v_max
                t = i / ramp
                return v_min + (v_max - v_min) * (1 - math.cos(math.pi * t)) / 2
            elif i < ramp + cruise:
                return v_max
            else:
                # S-curve decel
                j = i - ramp - cruise
                t = j / ramp
                return v_max - (v_max - v_min) * (1 - math.cos(math.pi * t)) / 2

        # Build pulses with variable timing
        # Pigpio max ~5500 pulses per wave_add_generic, so we chunk
        MAX_PULSES_PER_WAVE = 2500  # 2500 steps = 5000 pulses

        all_pulses = []
        for i in range(steps):
            v = speed_at(i)
            half_us = max(10, int(1_000_000 / (2 * v)))
            all_pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
            all_pulses.append(pigpio.pulse(0, STEP_MASK, half_us))

        # If fits in one wave — perfect, no chunking
        if steps <= MAX_PULSES_PER_WAVE:
            self.pi.wave_clear()
            self.pi.wave_add_generic(all_pulses)
            wid = self.pi.wave_create()
            return wid

        # For longer moves: create multiple waves and chain them
        # Returns -1 to signal caller should use _move_accel_chained
        return -2  # special code: use chained approach

    def _move_accel_chained(self, a_dir: int, b_dir: int, steps: int, speed: int, stop_sensor: int | None = None) -> bool:
        """Move with smooth S-curve acceleration using chained waves.

        For moves longer than ~2500 steps, creates multiple waves
        and chains them. Each wave has variable pulse widths within it,
        so transitions between waves are nearly seamless (same speed
        at boundary).
        """
        import math

        hit = False
        self.pi.write(MOTOR_A_DIR, a_dir)
        self.pi.write(MOTOR_B_DIR, b_dir)
        time.sleep(0.001)

        if stop_sensor is not None and self.sensor_stable(
            stop_sensor, reads=self.config.poll_reads,
            delay=self.config.poll_delay, need=self.config.poll_need,
        ):
            return True

        def _on_endstop(gpio, level, tick):
            nonlocal hit
            if self.sensor_stable(stop_sensor, reads=self.config.poll_reads,
                                   delay=self.config.poll_delay, need=self.config.poll_need):
                hit = True
                self.pi.wave_tx_stop()

        cb = None
        if stop_sensor is not None:
            cb = self.pi.callback(stop_sensor, pigpio.RISING_EDGE, _on_endstop)

        v_min = self.config.min_speed
        v_max = max(speed, v_min)
        ramp = min(self.config.accel_steps, steps // 3)
        cruise = steps - ramp * 2 if ramp >= 5 else 0

        def speed_at(i):
            if ramp < 5 or v_min >= v_max:
                return v_max
            if i < ramp:
                t = i / ramp
                return v_min + (v_max - v_min) * (1 - math.cos(math.pi * t)) / 2
            elif i < ramp + cruise:
                return v_max
            else:
                j = i - ramp - cruise
                t = j / ramp
                return v_max - (v_max - v_min) * (1 - math.cos(math.pi * t)) / 2

        # Build and send in chunks of 2000 steps
        CHUNK = 2000
        sent = 0

        while sent < steps and not hit:
            chunk_size = min(CHUNK, steps - sent)
            pulses = []
            for i in range(chunk_size):
                v = speed_at(sent + i)
                half_us = max(10, int(1_000_000 / (2 * v)))
                pulses.append(pigpio.pulse(STEP_MASK, 0, half_us))
                pulses.append(pigpio.pulse(0, STEP_MASK, half_us))

            self.pi.wave_clear()
            self.pi.wave_add_generic(pulses)
            wid = self.pi.wave_create()
            if wid < 0:
                print(f'  wave_create error at step {sent}')
                break

            self.pi.wave_send_once(wid)

            t0 = time.time()
            while self.pi.wave_tx_busy():
                time.sleep(0.001)
                if stop_sensor is not None and not hit:
                    if self.sensor_stable(stop_sensor, reads=self.config.poll_reads,
                                           delay=self.config.poll_delay, need=self.config.poll_need):
                        hit = True
                        self.pi.wave_tx_stop()
                        break
                if time.time() - t0 > self.config.timeout_main:
                    self.pi.wave_tx_stop()
                    print('  TIMEOUT')
                    break

            try:
                self.pi.wave_delete(wid)
            except pigpio.error:
                pass

            sent += chunk_size

        if cb:
            cb.cancel()
        self.pi.wave_clear()
        return hit

    def move(self, a_dir: int, b_dir: int, steps: int, speed: int, stop_sensor: int | None = None) -> bool:
        """
        Move with smooth S-curve acceleration.

        Uses variable pulse widths within each wave — no discrete speed steps,
        no gaps between segments. The result is buttery smooth acceleration
        and deceleration.

        For short moves (<2500 steps): single wave with all pulses.
        For long moves: chained waves, each with variable timing.
        """
        if steps <= 0:
            return False

        return self._move_accel_chained(a_dir, b_dir, steps, speed, stop_sensor)

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
        elif cmd == 'test-smooth':
            # Test smooth movement: 10000 steps right then back
            print('Smooth test: 10000 steps X+ at speed 3000...')
            motion.move(1, 1, 10000, 3000)
            time.sleep(0.5)
            print('Smooth test: 10000 steps X- back...')
            motion.move(0, 0, 10000, 3000)
            ok = True
        else:
            raise SystemExit(f'unknown command: {cmd}\nAvailable: home, x-sweep, y-sweep, test-smooth')
        print('FINAL', motion.state(), 'ok=', ok)
        return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else 'home'
    return run_command(cmd)


if __name__ == '__main__':
    raise SystemExit(main())
