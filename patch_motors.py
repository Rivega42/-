import re

with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

# Быстрая: chunk=500 → 1000
txt = txt.replace(
    "_move_with_endstop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=500)",
    "_move_with_endstop(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=1000)"
)
txt = txt.replace(
    "_move_with_endstop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME, chunk=500)",
    "_move_with_endstop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME, chunk=1000)"
)

# Медленная X: по 1 шагу → chunk 300
old_x = """        for _i in range(BACKOFF + 200):
            if self.pi.read(PIN_X_HOME):
                hit2 = True; break
            self.pi.wave_clear()
            self.pi.wave_add_generic([_pg2.pulse(_sm, 0, _pus), _pg2.pulse(0, _sm, _pus)])
            _wid = self.pi.wave_create()
            self.pi.wave_send_once(_wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.00005)
            self.pi.wave_delete(_wid)"""

new_x = """        _chunk_slow = 300
        for _i in range(0, BACKOFF + 200, _chunk_slow):
            if self.pi.read(PIN_X_HOME):
                hit2 = True; break
            _n = min(_chunk_slow, BACKOFF + 200 - _i)
            _wf = []
            for _ in range(_n):
                _wf.append(_pg2.pulse(_sm, 0, _pus))
                _wf.append(_pg2.pulse(0, _sm, _pus))
            self.pi.wave_clear()
            self.pi.wave_add_generic(_wf)
            _wid = self.pi.wave_create()
            self.pi.wave_send_once(_wid)
            while self.pi.wave_tx_busy():
                time.sleep(0.0001)
            self.pi.wave_delete(_wid)"""

txt = txt.replace(old_x, new_x)

# Медленная Y: по 5 шагов → chunk 300
old_y = """        for _i in range(0, BACKOFF + 200, 5):
            if self.pi.read(PIN_Y_HOME):
                hit2 = True; break
            _wf = []
            for _ in range(5):
                _wf.append(_pg2.pulse(_sm, 0, _pus))
                _wf.append(_pg2.pulse(0, _sm, _pus))"""

new_y = """        _chunk_slow = 300
        for _i in range(0, BACKOFF + 200, _chunk_slow):
            if self.pi.read(PIN_Y_HOME):
                hit2 = True; break
            _n = min(_chunk_slow, BACKOFF + 200 - _i)
            _wf = []
            for _ in range(_n):
                _wf.append(_pg2.pulse(_sm, 0, _pus))
                _wf.append(_pg2.pulse(0, _sm, _pus))"""

txt = txt.replace(old_y, new_y)

with open("bookcabinet/hardware/motors.py", "w") as f:
    f.write(txt)
print("OK — быстрая=1000, медленная=300")
