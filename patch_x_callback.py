with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X быстрая: chunks → callback glitch=0
txt = txt.replace(
    "hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)",
    "hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, glitch_us=0)"
)

# X медленная: chunks → callback glitch=0
txt = txt.replace(
    "hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=50)",
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=0)"
)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — X callback glitch=0, Y callback glitch=0")
