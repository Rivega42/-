#!/usr/bin/env python3
"""
BookCabinet — Tray Platform Control

Управление платформой (лотком) шкафа.

GPIO пины (BCM):
  TRAY_STEP = 18    # Шаг мотора
  TRAY_DIR  = 27    # Направление: 0=вперёд (FRONT), 1=назад (BACK)
  TRAY_EN1  = 25    # Enable 1: LOW=работа, HIGH=отключен
  TRAY_EN2  = 26    # Enable 2: LOW=работа, HIGH=отключен

Концевики:
  ENDSTOP_FRONT = 7   # Передний: 1=нажат, 0=свободен
  ENDSTOP_BACK  = 20  # Задний: 1=нажат, 0=свободен

Параметры:
  TRAY_FREQ = 12000 Hz  # Оптимальная частота (тихо + надёжно)
  Total travel: ~21000 шагов
  Center: ~10500 шагов

Использование:
  python3 tray_platform.py calibrate  # Калибровка: FRONT -> BACK -> CENTER
  python3 tray_platform.py front      # Двигать к FRONT
  python3 tray_platform.py back       # Двигать к BACK
  python3 tray_platform.py center     # Двигать в центр (после калибровки)
  python3 tray_platform.py status     # Показать состояние концевиков
"""

import pigpio
import time
import sys

# === GPIO PINS ===
TRAY_STEP = 18
TRAY_DIR = 27
TRAY_EN1 = 25
TRAY_EN2 = 26
ENDSTOP_FRONT = 7
ENDSTOP_BACK = 20

# === PARAMETERS ===
TRAY_FREQ = 12000  # Hz


class TrayPlatform:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Cannot connect to pigpiod")
        
        self.total_steps = 0
        self.center_steps = 0
        self.wave_id = None
        
        self._setup_pins()
    
    def _setup_pins(self):
        """Настройка GPIO пинов."""
        for pin in [TRAY_STEP, TRAY_DIR, TRAY_EN1, TRAY_EN2]:
            self.pi.set_mode(pin, pigpio.OUTPUT)
        
        # Драйвер выключен по умолчанию
        self.pi.write(TRAY_EN1, 1)
        self.pi.write(TRAY_EN2, 1)
        
        for pin in [ENDSTOP_FRONT, ENDSTOP_BACK]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
            self.pi.set_glitch_filter(pin, 300)  # 300μs filter — prevents bounce
    
    def _create_wave(self):
        """Создать wave для генерации импульсов."""
        period_us = int(1000000 / TRAY_FREQ)
        pulse_us = period_us // 2
        
        self.pi.wave_clear()
        waveform = [
            pigpio.pulse(1 << TRAY_STEP, 0, pulse_us),
            pigpio.pulse(0, 1 << TRAY_STEP, pulse_us)
        ]
        self.pi.wave_add_generic(waveform)
        self.wave_id = self.pi.wave_create()
    
    def _delete_wave(self):
        """Удалить wave."""
        if self.wave_id is not None:
            self.pi.wave_delete(self.wave_id)
            self.wave_id = None
        self.pi.wave_clear()
    
    def enable(self):
        """Включить драйвер мотора."""
        self.pi.write(TRAY_EN1, 0)
        self.pi.write(TRAY_EN2, 0)
    
    def disable(self):
        """Выключить драйвер мотора."""
        self.pi.write(TRAY_EN1, 1)
        self.pi.write(TRAY_EN2, 1)
    
    def status(self) -> dict:
        """Получить состояние концевиков."""
        return {
            'FRONT': self.pi.read(ENDSTOP_FRONT),
            'BACK': self.pi.read(ENDSTOP_BACK),
        }
    
    def move_until(self, direction: int, endstop_pin: int, max_time: float = 15.0) -> tuple:
        """
        Двигать платформу до срабатывания концевика.
        
        Args:
            direction: 0=вперёд (FRONT), 1=назад (BACK)
            endstop_pin: GPIO пин концевика
            max_time: Максимальное время движения (секунды)
        
        Returns:
            (steps, reached): количество шагов и флаг достижения концевика
        """
        self.pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        
        self.pi.wave_send_repeat(self.wave_id)
        
        start = time.time()
        while self.pi.read(endstop_pin) == 0 and (time.time() - start) < max_time:
            time.sleep(0.0005)
        
        self.pi.wave_tx_stop()
        elapsed = time.time() - start
        steps = int(elapsed * TRAY_FREQ)
        reached = self.pi.read(endstop_pin) == 1
        
        return steps, reached
    
    def move_steps(self, direction: int, steps: int):
        """
        Двигать платформу на заданное количество шагов.
        
        Args:
            direction: 0=вперёд (FRONT), 1=назад (BACK)
            steps: Количество шагов
        """
        self.pi.write(TRAY_DIR, direction)
        time.sleep(0.01)
        
        self.pi.wave_send_repeat(self.wave_id)
        time.sleep(steps / TRAY_FREQ)
        self.pi.wave_tx_stop()
    
    def calibrate(self) -> bool:
        """
        Калибровка платформы: FRONT -> BACK -> CENTER.
        
        Returns:
            True если калибровка успешна
        """
        print(f"=== TRAY CALIBRATION at {TRAY_FREQ} Hz ===")
        
        self.enable()
        self._create_wave()
        
        try:
            # Step 1: Move to FRONT
            print("Moving to FRONT...")
            steps_to_front, reached = self.move_until(0, ENDSTOP_FRONT)
            if not reached:
                print("FRONT FAIL!")
                return False
            print(f"FRONT done after {steps_to_front} steps")
            time.sleep(0.3)
            
            # Step 2: Move to BACK (measure total travel)
            print("Moving to BACK...")
            self.total_steps, reached = self.move_until(1, ENDSTOP_BACK)
            if not reached:
                print("BACK FAIL!")
                return False
            print(f"BACK done after {self.total_steps} steps")
            time.sleep(0.3)
            
            # Step 3: Move to CENTER
            print("Moving to CENTER...")
            self.center_steps = self.total_steps // 2
            self.move_steps(0, self.center_steps)
            print(f"CENTER at {self.center_steps} steps")
            
            print(f"=== Total travel: {self.total_steps} steps ===")
            return True
            
        finally:
            self._delete_wave()
            self.disable()
    
    def go_front(self) -> bool:
        """Двигать к FRONT."""
        print("Moving to FRONT...")
        self.enable()
        self._create_wave()
        try:
            steps, reached = self.move_until(0, ENDSTOP_FRONT)
            status = "done" if reached else "FAIL"
            print(f"FRONT {status} after {steps} steps")
            return reached
        finally:
            self._delete_wave()
            self.disable()
    
    def go_back(self) -> bool:
        """Двигать к BACK."""
        print("Moving to BACK...")
        self.enable()
        self._create_wave()
        try:
            steps, reached = self.move_until(1, ENDSTOP_BACK)
            status = "done" if reached else "FAIL"
            print(f"BACK {status} after {steps} steps")
            return reached
        finally:
            self._delete_wave()
            self.disable()
    
    def go_center(self):
        """Двигать в центр (требует предварительной калибровки)."""
        if self.total_steps == 0:
            print("ERROR: Run calibrate first!")
            return
        
        print("Moving to CENTER...")
        self.enable()
        self._create_wave()
        try:
            # Сначала к FRONT, потом к центру
            self.move_until(0, ENDSTOP_FRONT)
            time.sleep(0.2)
            self.move_steps(1, self.center_steps)
            print(f"CENTER at {self.center_steps} steps")
        finally:
            self._delete_wave()
            self.disable()
    
    def close(self):
        """Закрыть соединение."""
        self._delete_wave()
        self.disable()
        self.pi.stop()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    cmd = sys.argv[1]
    tray = TrayPlatform()
    
    try:
        if cmd == 'calibrate':
            ok = tray.calibrate()
            return 0 if ok else 1
        elif cmd == 'front':
            ok = tray.go_front()
            return 0 if ok else 1
        elif cmd == 'back':
            ok = tray.go_back()
            return 0 if ok else 1
        elif cmd == 'center':
            tray.calibrate()  # Need calibration first
            return 0
        elif cmd == 'status':
            status = tray.status()
            print(f"FRONT (GPIO {ENDSTOP_FRONT}): {'PRESSED' if status['FRONT'] else 'free'}")
            print(f"BACK (GPIO {ENDSTOP_BACK}): {'PRESSED' if status['BACK'] else 'free'}")
            return 0
        else:
            print(f"Unknown command: {cmd}")
            print(__doc__)
            return 1
    finally:
        tray.close()


if __name__ == '__main__':
    sys.exit(main())
