with open("bookcabinet/hardware/motors.py") as f:
    txt = f.read()

old_move = '''async def move_corexy(self, axis: str, steps: int) -> bool:
        """Move along CoreXY axis (X or Y)"""
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            axis = axis.upper()
            
            if self.mock_mode:
                await asyncio.sleep(0.5)
                return True
            
            if axis == "X":
                # X: both motors same direction
                dir_val = 1 if steps > 0 else 0
                self.pi.write(GPIO_PINS["MOTOR_A_DIR"], dir_val)
                self.pi.write(GPIO_PINS["MOTOR_B_DIR"], dir_val)
            elif axis == "Y":
                # Y: motors opposite directions
                if steps > 0:
                    self.pi.write(GPIO_PINS["MOTOR_A_DIR"], 1)
                    self.pi.write(GPIO_PINS["MOTOR_B_DIR"], 0)
                else:
                    self.pi.write(GPIO_PINS["MOTOR_A_DIR"], 0)
                    self.pi.write(GPIO_PINS["MOTOR_B_DIR"], 1)
            else:
                return False
            
            time.sleep(0.01)
            self._wave_steps(
                [GPIO_PINS["MOTOR_A_STEP"], GPIO_PINS["MOTOR_B_STEP"]],
                abs(steps),
                MOTOR_SPEEDS["xy"]
            )
            
            return True
        finally:
            self.is_moving = False'''

new_move = '''async def move_corexy(self, axis: str, steps: int) -> bool:
        """Move along CoreXY axis with endstop protection.
        Автоматически ставит callback на концевик в сторону движения.
        При срабатывании — мгновенный стоп DMA."""
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            axis = axis.upper()
            
            if self.mock_mode:
                await asyncio.sleep(0.5)
                return True
            
            import pigpio
            
            # Определяем направление и концевик
            endstop_pin = None
            if axis == "X":
                dir_val = 1 if steps > 0 else 0
                self.pi.write(GPIO_PINS["MOTOR_A_DIR"], dir_val)
                self.pi.write(GPIO_PINS["MOTOR_B_DIR"], dir_val)
                # X+ (вправо) → SENSOR_X_END, X- (влево) → SENSOR_X_BEGIN
                endstop_pin = GPIO_PINS["SENSOR_X_END"] if steps > 0 else GPIO_PINS["SENSOR_X_BEGIN"]
            elif axis == "Y":
                if steps > 0:
                    self.pi.write(GPIO_PINS["MOTOR_A_DIR"], 1)
                    self.pi.write(GPIO_PINS["MOTOR_B_DIR"], 0)
                else:
                    self.pi.write(GPIO_PINS["MOTOR_A_DIR"], 0)
                    self.pi.write(GPIO_PINS["MOTOR_B_DIR"], 1)
                # Y+ (вверх) → SENSOR_Y_END, Y- (вниз) → SENSOR_Y_BEGIN
                endstop_pin = GPIO_PINS["SENSOR_Y_END"] if steps > 0 else GPIO_PINS["SENSOR_Y_BEGIN"]
            else:
                return False
            
            time.sleep(0.001)
            
            # Если уже на концевике — не ехать
            if self.pi.read(endstop_pin):
                print(f"[move] {axis} pin {endstop_pin} уже HIGH, движение отменено")
                return False
            
            # Glitch filter 500us: фильтрует спайки от DIR/STEP, пропускает реальное нажатие
            GLITCH_US = 500
            self.pi.set_glitch_filter(endstop_pin, GLITCH_US)
            time.sleep(0.005)
            
            # Callback: мгновенный стоп при концевике
            hit_flag = [False]
            def _on_endstop(gpio, level, tick):
                if level == 1:
                    self.pi.wave_tx_stop()
                    hit_flag[0] = True
            
            cb = self.pi.callback(endstop_pin, pigpio.RISING_EDGE, _on_endstop)
            
            # Движение wave чанками
            step_pins = [GPIO_PINS["MOTOR_A_STEP"], GPIO_PINS["MOTOR_B_STEP"]]
            step_mask = (1 << step_pins[0]) | (1 << step_pins[1])
            pulse_us = int(500000 / MOTOR_SPEEDS["xy"])
            total = abs(steps)
            chunk = 2000
            done = 0
            
            while done < total and not hit_flag[0]:
                remaining = min(chunk, total - done)
                wf = []
                for _ in range(remaining):
                    wf.append(pigpio.pulse(step_mask, 0, pulse_us))
                    wf.append(pigpio.pulse(0, step_mask, pulse_us))
                self.pi.wave_clear()
                self.pi.wave_add_generic(wf)
                wid = self.pi.wave_create()
                if wid < 0:
                    break
                self.pi.wave_send_once(wid)
                while self.pi.wave_tx_busy():
                    time.sleep(0.0005)
                self.pi.wave_delete(wid)
                done += remaining
            
            # Cleanup
            cb.cancel()
            self.pi.set_glitch_filter(endstop_pin, 0)
            
            if hit_flag[0]:
                print(f"[move] {axis} ENDSTOP HIT at ~{done} steps (pin {endstop_pin})")
            
            return True
        finally:
            self.is_moving = False'''

if old_move in txt:
    txt = txt.replace(old_move, new_move)
    with open("bookcabinet/hardware/motors.py", "w") as f:
        f.write(txt)
    print("OK — move_corexy with endstop protection")
else:
    print("ERROR: old block not found")
