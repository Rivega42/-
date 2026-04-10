with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# После backoff X — ждём пока сенсор отпустится
old_x = '''        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная
        hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 200, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)'''

new_x = '''        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Ждём пока сенсор отпустится после backoff
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
        hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)'''

# После backoff Y
old_y = '''        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Медленная
        hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 200, SLOW_SPEED, PIN_Y_HOME, glitch_us=1000)'''

new_y = '''        self._wave_steps(step_pins, BACKOFF, FAST_SPEED)
        time.sleep(0.1)
        # Ждём пока сенсор отпустится после backoff
        for _w in range(50):
            if not self.pi.read(PIN_Y_HOME):
                break
            time.sleep(0.01)
        else:
            print("[homing] WARN: Y сенсор не отпустился после backoff, увеличиваю отъезд")
            self.pi.write(PIN_A_DIR, 1)
            self.pi.write(PIN_B_DIR, 0)
            time.sleep(0.001)
            self._wave_steps(step_pins, 300, FAST_SPEED)
            time.sleep(0.1)
        # Медленная
        hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 500, SLOW_SPEED, PIN_Y_HOME, glitch_us=1000)'''

txt = txt.replace(old_x, new_x)
txt = txt.replace(old_y, new_y)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — backoff wait + extra backoff if stuck")
