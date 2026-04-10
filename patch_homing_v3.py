with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

old = '''        def _move_with_glitch_stop(a_dir, b_dir, steps, speed, sensor_pin, glitch_us=5000):
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
            return hit_flag[0] or self.pi.read(sensor_pin)'''

new = '''        def _move_with_glitch_stop(a_dir, b_dir, steps, speed, sensor_pin, glitch_us=5000):
            """Один большой wave + glitch filter + callback = мгновенный стоп."""
            import pigpio as _pg

            # Если уже на концевике — сразу выход
            if self.pi.read(sensor_pin):
                print(f"[homing] pin {sensor_pin} уже HIGH, пропуск движения")
                return True

            # Glitch filter: игнорирует наводки короче glitch_us
            self.pi.set_glitch_filter(sensor_pin, glitch_us)
            time.sleep(0.01)  # дать фильтру стабилизироваться

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
            return hit_flag[0] or self.pi.read(sensor_pin)'''

if old in txt:
    txt = txt.replace(old, new)
    with open("bookcabinet/hardware/motors.py", "w") as f:
        f.write(txt)
    print("OK — added pre-check + glitch stabilization")
else:
    print("ERROR: old block not found")
