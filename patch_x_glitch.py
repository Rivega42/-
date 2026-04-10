with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# X медленная: glitch=0 → 1000
txt = txt.replace(
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=0)",
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)"
)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — X slow glitch=1000, Y slow glitch=0")
