"""Replace homing with glitch_filter + callback + wave_tx_stop approach"""

with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# Find and replace the entire homing body (from _move_with_endstop to return True)
old = '''        def _move_with_endstop(a_dir, b_dir, steps, speed, sensor_pin, chunk=50):
            import pigpio as _pg
            self.pi.write(PIN_A_DIR, a_dir)
            self.pi.write(PIN_B_DIR, b_dir)
            time.sleep(0.001)

            pulse_us = int(500000 / speed)
            step_mask = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

            done = 0
            while done < steps:
                # Проверяем МЕЖДУ чанками (моторы стоят, нет наводок)
                if self.pi.read(sensor_pin):
                    return True
                remaining = min(chunk, steps - done)
                wf = []
                for _ in range(remaining):
                    wf.append(_pg.pulse(step_mask, 0, pulse_us))
                    wf.append(_pg.pulse(0, step_mask, pulse_us))
                self.pi.wave_clear()
                self.pi.wave_add_generic(wf)
                wid = self.pi.wave_create()
                if wid < 0:
                    return False
                self.pi.wave_send_once(wid)
                while self.pi.wave_tx_busy():
                    time.sleep(0.0001)
                self.pi.wave_delete(wid)
                done += remaining
            return self.pi.read(sensor_pin)


        print("[homing] Начало хоминга XY (wave_steps + callback)")

        # === X HOME → правый ===
        hit = _move_with_endstop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=1000)
        print(f"[homing] X быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд через move_corexy
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная фаза
        # X медленная: маленькие wave + pi.read
        import pigpio as _pg2
        self.pi.write(PIN_A_DIR, 1)
        self.pi.write(PIN_B_DIR, 1)
        time.sleep(0.001)
        _sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)
        _pus = int(500000 / SLOW_SPEED)
        hit2 = False
        _chunk_slow = 300
        for _i in range(0, BACKOFF + 200, _chunk_slow):
            if self.pi.read(PIN_X_HOME):
                hit2 = True; break
            _n = min(_chunk_slow, BACKOFF + 200 - _i)
            _wf = []
            for _ in range(_n):
                _wf.append(_pg2.pulse(_sm, 0, _pus))
                _wf.append(_pg2.pulse(0, _sm, _pus))
            self.pi.wave_clear()
            self.pi.wave_add_generic(_wf)
            _wid = self.pi.wave_create()
            self.pi.wave_send_once(_wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.0001)
            self.pi.wave_delete(_wid)
        print(f"[homing] X точная: {'HIT' if hit2 else 'MISS'}")
        self.position["x"] = 0
        time.sleep(0.2)

        # === Y HOME → нижний ===
        hit = _move_with_endstop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME, chunk=1000)
        print(f"[homing] Y быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд
        self.pi.write(PIN_A_DIR, 1)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная фаза
        # Y медленная: маленькие wave + pi.read (callback ненадёжен с DMA)
        import pigpio as _pg2
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 1)
        time.sleep(0.001)
        _sm = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)
        _pus = int(500000 / SLOW_SPEED)
        hit2 = False
        _chunk_slow = 300
        for _i in range(0, BACKOFF + 200, _chunk_slow):
            if self.pi.read(PIN_Y_HOME):
                hit2 = True; break
            _n = min(_chunk_slow, BACKOFF + 200 - _i)
            _wf = []
            for _ in range(_n):
                _wf.append(_pg2.pulse(_sm, 0, _pus))
                _wf.append(_pg2.pulse(0, _sm, _pus))
            self.pi.wave_clear()
            self.pi.wave_add_generic(_wf)
            _wid = self.pi.wave_create()
            self.pi.wave_send_once(_wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.0001)
            self.pi.wave_delete(_wid)
        print(f"[homing] Y точная: {'HIT' if hit2 else 'MISS'}")
        self.position["y"] = 0

        print(f"[homing] Готово. Позиция: {self.position}")
        return True'''

new = '''        def _move_with_glitch_stop(a_dir, b_dir, steps, speed, sensor_pin, glitch_us=5000):
            """Один большой wave + glitch filter + callback = мгновенный стоп."""
            import pigpio as _pg
            # Glitch filter: игнорирует наводки короче glitch_us
            self.pi.set_glitch_filter(sensor_pin, glitch_us)

            # Callback: при срабатывании концевика — мгновенный стоп DMA
            hit_flag = [False]
            def _on_endstop(gpio, level, tick):
                if level == 1:  # HIGH = нажат
                    self.pi.wave_tx_stop()
                    hit_flag[0] = True

            cb = self.pi.callback(sensor_pin, pigpio.RISING_EDGE, _on_endstop)

            self.pi.write(PIN_A_DIR, a_dir)
            self.pi.write(PIN_B_DIR, b_dir)
            time.sleep(0.001)

            pulse_us = int(500000 / speed)
            step_mask = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

            # Строим wave чанками по 2000 (лимит pigpio ~12000 pulses)
            chunk = 2000
            done = 0
            while done < steps and not hit_flag[0]:
                remaining = min(chunk, steps - done)
                wf = []
                for _ in range(remaining):
                    wf.append(_pg.pulse(step_mask, 0, pulse_us))
                    wf.append(_pg.pulse(0, step_mask, pulse_us))
                self.pi.wave_clear()
                self.pi.wave_add_generic(wf)
                wid = self.pi.wave_create()
                if wid < 0:
                    break
                self.pi.wave_send_once(wid)
                while self.pi.wave_tx_busy():
                    time.sleep(0.0005)
                self.pi.wave_delete(wid)
                done += remaining

            # Cleanup
            cb.cancel()
            self.pi.set_glitch_filter(sensor_pin, 0)
            return hit_flag[0] or self.pi.read(sensor_pin)


        print("[homing] Начало хоминга XY (glitch_filter + callback)")

        # === X HOME → правый ===
        hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME)
        print(f"[homing] X быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная фаза — тот же подход, но на малой скорости и glitch=1000
        hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 200, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)
        print(f"[homing] X точная: {'HIT' if hit2 else 'MISS'}")
        self.position["x"] = 0
        time.sleep(0.2)

        # === Y HOME → нижний ===
        hit = _move_with_glitch_stop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME)
        print(f"[homing] Y быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд
        self.pi.write(PIN_A_DIR, 1)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная
        hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 200, SLOW_SPEED, PIN_Y_HOME, glitch_us=1000)
        print(f"[homing] Y точная: {'HIT' if hit2 else 'MISS'}")
        self.position["y"] = 0

        print(f"[homing] Готово. Позиция: {self.position}")
        return True'''

if old in txt:
    txt = txt.replace(old, new)
    with open("bookcabinet/hardware/motors.py", "w") as f:
        f.write(txt)
    print("OK — glitch_filter + callback version")
else:
    print("ERROR: old block not found")
