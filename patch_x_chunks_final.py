with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X быстрая: callback → chunks 200
txt = txt.replace(
    "hit = _move_with_glitch_stop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, glitch_us=500)",
    "hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)"
)

# X медленная: callback → chunks 25
txt = txt.replace(
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=500)",
    "hit2 = _move_with_chunks(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, chunk=25)"
)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — X=chunks(200/25), Y=callback")
