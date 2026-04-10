with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# Для медленной фазы: glitch_us=1000 -> glitch_us=0 (без фильтра)
# На малой скорости наводки слабые, фильтр только мешает

# X медленная
txt = txt.replace(
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=1000)",
    "hit2 = _move_with_glitch_stop(1, 1, BACKOFF + 500, SLOW_SPEED, PIN_X_HOME, glitch_us=0)"
)

# Y медленная
txt = txt.replace(
    "hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 500, SLOW_SPEED, PIN_Y_HOME, glitch_us=1000)",
    "hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 500, SLOW_SPEED, PIN_Y_HOME, glitch_us=0)"
)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — slow phase glitch_us=0")
