with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X быстрая: chunks → callback glitch=500
txt = txt.replace(
    "hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)",
    "hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, glitch_us=500)"
)

# X медленная: chunks → callback glitch=500
txt = txt.replace(
    "hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=50)",
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=500)"
)

# Y быстрая: glitch 5000 → 500 (унифицируем)
txt = txt.replace(
    "hit = _move_with_glitch_stop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME)",
    "hit = _move_with_glitch_stop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME, glitch_us=500)"
)

# Y медленная: оставляем glitch=0 (работает идеально)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — homing X glitch=500, Y fast glitch=500, Y slow glitch=0")
