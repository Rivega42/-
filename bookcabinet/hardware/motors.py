"""
Управление моторами CoreXY и платформой
Использует pigpio hardware waves для плавной работы (DMA)
"""
import asyncio
import time
from typing import Tuple
from ..config import GPIO_PINS, MOTOR_SPEEDS, MOCK_MODE, TIMEOUTS


class Motors:
    def __init__(self):
        self.position = {"x": 0, "y": 0, "tray": 0}
        self.is_moving = False
        self.mock_mode = MOCK_MODE
        self.pi = None
        
        if not self.mock_mode:
            try:
                import pigpio
                self.pi = pigpio.pi()
                if not self.pi.connected:
                    print("WARNING: pigpio not connected, switching to mock mode")
                    self.mock_mode = True
                else:
                    # Setup output pins
                    for pin_name in ["MOTOR_A_STEP", "MOTOR_A_DIR", "MOTOR_B_STEP", "MOTOR_B_DIR", "TRAY_STEP", "TRAY_DIR"]:
                        self.pi.set_mode(GPIO_PINS[pin_name], pigpio.OUTPUT)
                        self.pi.write(GPIO_PINS[pin_name], 0)
            except ImportError:
                print("WARNING: pigpio not installed, switching to mock mode")
                self.mock_mode = True
    
    def _wave_steps(self, step_pins: list, steps: int, frequency: int = 4000) -> bool:
        """Execute steps using hardware waves (DMA) for smooth operation"""
        if self.mock_mode or not self.pi:
            return True
        
        import pigpio
        pulse_us = int(500000 / frequency)
        
        # Create wave mask for step pins
        step_mask = 0
        for pin in step_pins:
            step_mask |= (1 << pin)
        
        self.pi.wave_clear()
        
        # Build wave with 200 steps per chunk
        chunk_size = min(200, steps)
        wf = []
        for _ in range(chunk_size):
            wf.append(pigpio.pulse(step_mask, 0, pulse_us))
            wf.append(pigpio.pulse(0, step_mask, pulse_us))
        
        self.pi.wave_add_generic(wf)
        wave_id = self.pi.wave_create()
        
        if wave_id < 0:
            return False
        
        # Calculate repeats
        repeats = steps // chunk_size
        remainder = steps % chunk_size
        
        if repeats > 0:
            chain = [255, 0, wave_id, 255, 1, repeats & 0xFF, (repeats >> 8) & 0xFF]
            self.pi.wave_chain(chain)
            
            while self.pi.wave_tx_busy():
                time.sleep(0.01)
        
        self.pi.wave_delete(wave_id)
        
        # Handle remainder
        if remainder > 0:
            self.pi.wave_clear()
            wf = []
            for _ in range(remainder):
                wf.append(pigpio.pulse(step_mask, 0, pulse_us))
                wf.append(pigpio.pulse(0, step_mask, pulse_us))
            self.pi.wave_add_generic(wf)
            wave_id = self.pi.wave_create()
            
            if wave_id >= 0:
                self.pi.wave_send_once(wave_id)
                while self.pi.wave_tx_busy():
                    time.sleep(0.01)
                self.pi.wave_delete(wave_id)
        
        return True
    
    async def move_xy(self, target_x: int, target_y: int) -> bool:
        """Move to target position using CoreXY kinematics"""
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            dx = target_x - self.position["x"]
            dy = target_y - self.position["y"]
            
            # CoreXY kinematics
            steps_a = dx + dy
            steps_b = -dx + dy
            
            dir_a = 1 if steps_a > 0 else 0
            dir_b = 1 if steps_b > 0 else 0
            
            if self.mock_mode:
                await asyncio.sleep(TIMEOUTS["move"] / 1000)
            else:
                # Set directions
                self.pi.write(GPIO_PINS["MOTOR_A_DIR"], dir_a)
                self.pi.write(GPIO_PINS["MOTOR_B_DIR"], dir_b)
                time.sleep(0.01)
                
                # Move both motors simultaneously
                max_steps = max(abs(steps_a), abs(steps_b))
                if max_steps > 0:
                    step_pins = []
                    if abs(steps_a) > 0:
                        step_pins.append(GPIO_PINS["MOTOR_A_STEP"])
                    if abs(steps_b) > 0:
                        step_pins.append(GPIO_PINS["MOTOR_B_STEP"])
                    
                    self._wave_steps(step_pins, max_steps, MOTOR_SPEEDS["xy"])
            
            self.position["x"] = target_x
            self.position["y"] = target_y
            return True
            
        finally:
            self.is_moving = False
    
    async def move_tray(self, direction: str, steps: int = 3000) -> bool:
        """Move tray in/out"""
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            is_extend = direction in ("extend", "out", "+")
            
            if self.mock_mode:
                timeout = TIMEOUTS["tray_extend"] if is_extend else TIMEOUTS["tray_retract"]
                await asyncio.sleep(timeout / 1000)
            else:
                self.pi.write(GPIO_PINS["TRAY_DIR"], 1 if is_extend else 0)
                time.sleep(0.01)
                self._wave_steps([GPIO_PINS["TRAY_STEP"]], steps, MOTOR_SPEEDS["tray"])
            
            self.position["tray"] = 1 if is_extend else 0
            return True
            
        finally:
            self.is_moving = False
    
    async def extend_tray(self, steps: int = 3000) -> bool:
        return await self.move_tray("extend", steps)
    
    async def retract_tray(self, steps: int = 3000) -> bool:
        return await self.move_tray("retract", steps)
    
    def get_position(self) -> dict:
        return self.position.copy()
    
    def stop(self):
        """Emergency stop"""
        self.is_moving = False
        if self.pi and not self.mock_mode:
            self.pi.wave_tx_stop()
            self.pi.write(GPIO_PINS["MOTOR_A_STEP"], 0)
            self.pi.write(GPIO_PINS["MOTOR_B_STEP"], 0)
            self.pi.write(GPIO_PINS["TRAY_STEP"], 0)
    
    async def home(self) -> bool:
        """Move to home position (0, 0)"""
        result = await self.move_xy(0, 0)
        if result:
            await self.retract_tray()
        return result

    def _read_pin_direct(self, pin: int) -> bool:
        """Прямое чтение пина без debounce — для хоминга"""
        if self.mock_mode:
            return False
        readings = [self.pi.read(pin) for _ in range(5)]
        return sum(readings) >= 3

    async def home_with_sensors(self, sensors) -> bool:
        """
        Хоминг XY: move_corexy-style (_wave_steps) + pigpio callback на концевик.
        1. Быстрая: _wave_steps @ xy speed, callback стопит wave_tx мгновенно
        2. Отъезд через move_corexy
        3. Медленная: _wave_steps @ 1000, callback стопит точно
        """
        import pigpio
        FAST_SPEED = 1000  # homing fast speed
        SLOW_SPEED = 300
        MAX_STEPS = 80000
        BACKOFF = 300

        PIN_A_STEP = GPIO_PINS["MOTOR_A_STEP"]
        PIN_A_DIR  = GPIO_PINS["MOTOR_A_DIR"]
        PIN_B_STEP = GPIO_PINS["MOTOR_B_STEP"]
        PIN_B_DIR  = GPIO_PINS["MOTOR_B_DIR"]
        PIN_X_HOME = GPIO_PINS["SENSOR_X_END"]
        PIN_Y_HOME = GPIO_PINS["SENSOR_Y_BEGIN"]

        step_pins = [PIN_A_STEP, PIN_B_STEP]

        if self.mock_mode:
            await asyncio.sleep(2.0)
            self.position["x"] = 0
            self.position["y"] = 0
            return True

        def _move_with_chunks(a_dir, b_dir, steps, speed, sensor_pin, chunk=200):
            """Chunk approach: маленькие wave, проверка сенсора между ними (моторы стоят)."""
            import pigpio as _pg
            self.pi.write(PIN_A_DIR, a_dir)
            self.pi.write(PIN_B_DIR, b_dir)
            time.sleep(0.001)

            pulse_us = int(500000 / speed)
            step_mask = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

            done = 0
            while done < steps:
                if self.pi.read(sensor_pin):
                    return True
                remaining = min(chunk, steps - done)
                wf = []
                for _ in range(remaining):
                    wf.append(_pg.pulse(step_mask, 0, pulse_us))
                    wf.append(_pg.pulse(0, step_mask, pulse_us))
                self.pi.wave_clear()
                self.pi.wave_add_generic(wf)
                wid = self.pi.wave_create()
                if wid < 0:
                    return False
                self.pi.wave_send_once(wid)
                while self.pi.wave_tx_busy():
                    time.sleep(0.0001)
                self.pi.wave_delete(wid)
                done += remaining
            return self.pi.read(sensor_pin)

        def _move_with_glitch_stop(a_dir, b_dir, steps, speed, sensor_pin, glitch_us=5000):
            """Один большой wave + glitch filter + callback = мгновенный стоп."""
            import pigpio as _pg

            # Если уже на концевике — сразу выход
            if self.pi.read(sensor_pin):
                print(f"[homing] pin {sensor_pin} уже HIGH, пропуск движения")
                return True

            # Glitch filter: игнорирует наводки короче glitch_us
            self.pi.set_glitch_filter(sensor_pin, glitch_us)
            time.sleep(0.01)  # дать фильтру стабилизироваться

            # Callback: при срабатывании концевика — мгновенный стоп DMA
            hit_flag = [False]
            def _on_endstop(gpio, level, tick):
                if level == 1:  # HIGH = нажат
                    self.pi.wave_tx_stop()
                    hit_flag[0] = True

            cb = self.pi.callback(sensor_pin, pigpio.RISING_EDGE, _on_endstop)

            self.pi.write(PIN_A_DIR, a_dir)
            self.pi.write(PIN_B_DIR, b_dir)
            time.sleep(0.001)

            pulse_us = int(500000 / speed)
            step_mask = (1 << PIN_A_STEP) | (1 << PIN_B_STEP)

            # Строим wave чанками по 2000 (лимит pigpio ~12000 pulses)
            chunk = 2000
            done = 0
            while done < steps and not hit_flag[0]:
                remaining = min(chunk, steps - done)
                wf = []
                for _ in range(remaining):
                    wf.append(_pg.pulse(step_mask, 0, pulse_us))
                    wf.append(_pg.pulse(0, step_mask, pulse_us))
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
            self.pi.set_glitch_filter(sensor_pin, 0)
            return hit_flag[0] or self.pi.read(sensor_pin)


        print("[homing] Начало хоминга XY (glitch_filter + callback)")

        # === X HOME → правый ===
        hit = _move_with_chunks(1, 1, MAX_STEPS, FAST_SPEED, PIN_X_HOME, chunk=200)
        print(f"[homing] X быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, 500, FAST_SPEED)
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
        hit2 = _move_with_chunks(1, 1, 1000, SLOW_SPEED, PIN_X_HOME, chunk=25)
        print(f"[homing] X точная: {'HIT' if hit2 else 'MISS'}")
        self.position["x"] = 0
        time.sleep(0.2)

        # === Y HOME → нижний ===
        hit = _move_with_glitch_stop(0, 1, MAX_STEPS, FAST_SPEED, PIN_Y_HOME, glitch_us=500)
        print(f"[homing] Y быстрая: {'HIT' if hit else 'MISS'}")
        # Отъезд
        self.pi.write(PIN_A_DIR, 1)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.001)
        self._wave_steps(step_pins, 500, FAST_SPEED)
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
        hit2 = _move_with_glitch_stop(0, 1, BACKOFF + 500, SLOW_SPEED, PIN_Y_HOME, glitch_us=0)
        print(f"[homing] Y точная: {'HIT' if hit2 else 'MISS'}")
        self.position["y"] = 0

        print(f"[homing] Готово. Позиция: {self.position}")
        return True

    async def home_tray_with_sensor(self, sensors) -> bool:
        """
        Хоминг лотка по концевику SENSOR_TRAY_BEGIN.
        ВАЖНО: вызывать ТОЛЬКО когда каретка в position x=0, y=0!
        Если каретка не в 0,0 — возвращает False с ошибкой.
        """
        if self.position["x"] != 0 or self.position["y"] != 0:
            print("[homing] ERROR: tray homing only allowed at x=0, y=0")
            return False

        HOMING_SPEED = 800
        HOMING_CHUNK = 100
        MAX_STEPS = 30000

        if self.mock_mode:
            await asyncio.sleep(1.0)
            self.position["tray"] = 0
            return True

        # Лоток назад (DIR=HIGH = назад по config)
        self.pi.write(GPIO_PINS["TRAY_DIR"], 1)
        time.sleep(0.01)
        total = 0
        # Debounce для SENSOR_TRAY_BEGIN (pin 20 - дребезг!)
        stable_count = 0
        while stable_count < 3 and total < MAX_STEPS:
            self._wave_steps([GPIO_PINS["TRAY_STEP"]], HOMING_CHUNK, HOMING_SPEED)
            total += HOMING_CHUNK
            if sensors.is_triggered("tray_begin"):
                stable_count += 1
            else:
                stable_count = 0
            await asyncio.sleep(0)

        self.position["tray"] = 0
        return True
    
    async def test_motor(self, motor: str, direction: int, steps: int = 500) -> bool:
        """Test individual motor"""
        if self.is_moving:
            return False
        
        self.is_moving = True
        try:
            motor = motor.upper()
            if motor == "A":
                step_pin = GPIO_PINS["MOTOR_A_STEP"]
                dir_pin = GPIO_PINS["MOTOR_A_DIR"]
            elif motor == "B":
                step_pin = GPIO_PINS["MOTOR_B_STEP"]
                dir_pin = GPIO_PINS["MOTOR_B_DIR"]
            else:
                return False
            
            if self.mock_mode:
                await asyncio.sleep(0.5)
            else:
                self.pi.write(dir_pin, 1 if direction > 0 else 0)
                time.sleep(0.01)
                self._wave_steps([step_pin], abs(steps), MOTOR_SPEEDS["xy"])
            
            return True
        finally:
            self.is_moving = False
    
    async def move_corexy(self, axis: str, steps: int) -> bool:
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
            self.is_moving = False


motors = Motors()
