"""
Калибровка системы
"""
import json
import os
from typing import Dict, Any, List
from ..config import CABINET


class Calibration:
    def __init__(self, filepath: str = 'bookcabinet/calibration.json'):
        self.filepath = filepath
        self.data = self._load()
    
    def _default_data(self) -> Dict[str, Any]:
        return {
            'kinematics': {
                'x_plus_dir_a': 1,
                'x_plus_dir_b': -1,
                'y_plus_dir_a': 1,
                'y_plus_dir_b': 1,
            },
            'positions': {
                'x': [0, 4500, 9000],
                'y': [i * 450 for i in range(21)],
            },
            'window': CABINET['window'],
            'grab_front': {
                'extend1': 1500,
                'retract': 1500,
                'extend2': 3000,
            },
            'grab_back': {
                'extend1': 1500,
                'retract': 1500,
                'extend2': 3000,
            },
            'speeds': {
                'xy': 4000,
                'tray': 2000,
                'acceleration': 8000,
            },
            'servos': {
                'lock1_open': 0,
                'lock1_close': 95,
                'lock2_open': 0,
                'lock2_close': 95,
            },
        }
    
    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                pass
        return self._default_data()
    
    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self.data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        keys = key.split('.')
        data = self.data
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self.save()
    
    def set_position_x(self, column: int, steps: int):
        self.data['positions']['x'][column] = steps
        self.save()
    
    def set_position_y(self, row: int, steps: int):
        self.data['positions']['y'][row] = steps
        self.save()
    
    def reset(self):
        self.data = self._default_data()
        self.save()


calibration = Calibration()
