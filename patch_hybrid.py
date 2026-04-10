with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# === Заменяем X хоминг на chunk-подход (без callback) ===
# X быстрая: callback → chunk
old_x_fast = '        hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME)'
new_x_fast = '        hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)'

# X медленная: callback → chunk  
old_x_slow = '        hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)'
new_x_slow = '        hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=50)'

txt = txt.replace(old_x_fast, new_x_fast)
txt = txt.replace(old_x_slow, new_x_slow)

# Добавляем _move_with_chunks прямо перед _move_with_glitch_stop
old_glitch_def = '        def _move_with_glitch_stop('
chunk_func = """        def _move_with_chunks(a_dir, b_dir, steps, speed, sensor_pin, chunk=200):
            \"\"\"Chunk approach: маленькие wave, проверка сенсора между ними (моторы стоят).\"\"\"
            import pigpio as _pg
            self.pi.write(PIN_A_DIR, a_dir)
            self.pi.write(PIN_B_DIR, b_dir)
            time.sleep(0.001)

            pulse_us = int(500000 / speed)
            step_mask = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

            done = 0
            while done < steps:
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

        def _move_with_glitch_stop("""

txt = txt.replace(old_glitch_def, chunk_func)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — X=chunks(200/50), Y=callback(glitch)")
