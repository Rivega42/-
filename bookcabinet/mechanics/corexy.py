"""
CoreXY кинематика
"""
from typing import Tuple
from ..config import CABINET


class CoreXY:
    def __init__(self):
        self.calibration = None
        self._load_calibration()
    
    def _load_calibration(self):
        self.calibration = {
            'positions_x': [0, 4500, 9000],
            'positions_y': [i * 450 for i in range(21)],
            'kinematics': {
                'x_plus_dir_a': 1,
                'x_plus_dir_b': -1,
                'y_plus_dir_a': 1,
                'y_plus_dir_b': 1,
            }
        }
    
    def cell_to_steps(self, row: str, x: int, y: int) -> Tuple[int, int]:
        steps_x = self.calibration['positions_x'][x]
        steps_y = self.calibration['positions_y'][y]
        return (steps_x, steps_y)
    
    def window_position(self) -> Tuple[int, int]:
        window = CABINET['window']
        return self.cell_to_steps(window['row'], window['x'], window['y'])
    
    def calculate_ab_steps(self, dx: int, dy: int) -> Tuple[int, int]:
        kin = self.calibration['kinematics']
        steps_a = dx * kin['x_plus_dir_a'] + dy * kin['y_plus_dir_a']
        steps_b = dx * kin['x_plus_dir_b'] + dy * kin['y_plus_dir_b']
        return (steps_a, steps_b)


corexy = CoreXY()
