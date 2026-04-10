with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X медленная: BACKOFF + 500 → 500 + 500 = уже 500 запас, но BACKOFF=300
# Нужно увеличить отъезд перед медленной фазой с BACKOFF(300) до 500

# X отъезд
txt = txt.replace(
    "self._wave_steps(step_pins, BACKOFF, FAST_SPEED)\n        time.sleep(0.1)\n        # Ждём пока сенсор отпустится после backoff\n        for _w in range(50):\n            if not self.pi.read(PIN_X_HOME):",
    "self._wave_steps(step_pins, 500, FAST_SPEED)\n        time.sleep(0.1)\n        # Ждём пока сенсор отпустится после backoff\n        for _w in range(50):\n            if not self.pi.read(PIN_X_HOME):"
)

# Y отъезд
txt = txt.replace(
    "self._wave_steps(step_pins, BACKOFF, FAST_SPEED)\n        time.sleep(0.1)\n        # Ждём пока сенсор отпустится после backoff\n        for _w in range(50):\n            if not self.pi.read(PIN_Y_HOME):",
    "self._wave_steps(step_pins, 500, FAST_SPEED)\n        time.sleep(0.1)\n        # Ждём пока сенсор отпустится после backoff\n        for _w in range(50):\n            if not self.pi.read(PIN_Y_HOME):"
)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — backoff 500")
