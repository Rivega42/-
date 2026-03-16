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
            chain = [255, 0, wave_id, 255, 1, repeats, 0]
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
        Хоминг XY по концевикам. Читает пины НАПРЯМУЮ без debounce.
        Один шаг за раз — мгновенная остановка при нажатии концевика.
        """
        HOMING_DELAY = 0.0005
        STEP_PULSE = 0.0001
        MAX_STEPS = 80000

        PIN_A_STEP = GPIO_PINS["MOTOR_A_STEP"]
        PIN_A_DIR  = GPIO_PINS["MOTOR_A_DIR"]
        PIN_B_STEP = GPIO_PINS["MOTOR_B_STEP"]
        PIN_B_DIR  = GPIO_PINS["MOTOR_B_DIR"]
        PIN_X_BEGIN = GPIO_PINS["SENSOR_X_BEGIN"]
        PIN_Y_BEGIN = GPIO_PINS["SENSOR_Y_BEGIN"]

        if self.mock_mode:
            import asyncio as _aio
            await _aio.sleep(2.0)
            self.position["x"] = 0
            self.position["y"] = 0
            return True

        print("[homing] Начало хоминга XY")

        # Хоминг X: CoreXY -X = A_DIR=0, B_DIR=1
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 1)
        time.sleep(0.01)

        for i in range(MAX_STEPS):
            if self._read_pin_direct(PIN_X_BEGIN):
                print(f"[homing] X концевик сработал на шаге {i}")
                break
            self.pi.write(PIN_A_STEP, 1)
            self.pi.write(PIN_B_STEP, 1)
            time.sleep(STEP_PULSE)
            self.pi.write(PIN_A_STEP, 0)
            self.pi.write(PIN_B_STEP, 0)
            time.sleep(HOMING_DELAY)
            if i % 500 == 0:
                await asyncio.sleep(0)
        else:
            print("[homing] WARN: X MAX_STEPS достигнут без концевика!")

        self.position["x"] = 0
        time.sleep(0.2)

        # Хоминг Y: CoreXY -Y = A_DIR=0, B_DIR=0
        self.pi.write(PIN_A_DIR, 0)
        self.pi.write(PIN_B_DIR, 0)
        time.sleep(0.01)

        for i in range(MAX_STEPS):
            if self._read_pin_direct(PIN_Y_BEGIN):
                print(f"[homing] Y концевик сработал на шаге {i}")
                break
            self.pi.write(PIN_A_STEP, 1)
            self.pi.write(PIN_B_STEP, 1)
            time.sleep(STEP_PULSE)
            self.pi.write(PIN_A_STEP, 0)
            self.pi.write(PIN_B_STEP, 0)
            time.sleep(HOMING_DELAY)
            if i % 500 == 0:
                await asyncio.sleep(0)
        else:
            print("[homing] WARN: Y MAX_STEPS достигнут без концевика!")

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
            self.is_moving = False


motors = Motors()
