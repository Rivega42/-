with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X быстрая: glitch_stop glitch=0 → chunks 200
txt = txt.replace(
    'hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, glitch_us=0)',
    'hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)'
)

# X медленная: glitch_stop glitch=1000 → chunks 25
# Также BACKOFF+200 → BACKOFF+500 (больше запас)
txt = txt.replace(
    'hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 200, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)',
    'hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=25)'
)

# Добавим backoff wait для X тоже (как у Y)
old_x_backoff = """        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная фаза — тот же подход, но на малой скорости и glitch=1000
        hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=25)"""

new_x_backoff = """        self._wave_steps(step_pins, 500, FAST_SPEED)
        time.sleep(0.1)
        # Ждём пока X сенсор отпустится после backoff
        for _w in range(50):
            if not self.pi.read(PIN_X_HOME):
                break
            time.sleep(0.01)
        else:
            print("[homing] WARN: X сенсор не отпустился после backoff, увеличиваю отъезд")
            self.pi.write(PIN_A_DIR, 0)
            self.pi.write(PIN_B_DIR, 0)
            time.sleep(0.001)
            self._wave_steps(step_pins, 300, FAST_SPEED)
            time.sleep(0.1)
        # Медленная
        hit2 = _move_with_chunks(1, 1, 1000, SLOW_SPEED, PIN_X_HOME, chunk=25)"""

txt = txt.replace(old_x_backoff, new_x_backoff)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK")
