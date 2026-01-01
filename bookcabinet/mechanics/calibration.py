"""
Калибровка системы v2.1
Полная поддержка wizard калибровки
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from ..config import CABINET


class CalibrationWizard:
    """Состояние wizard калибровки"""
    def __init__(self):
        self.mode: Optional[str] = None
        self.step: int = 0
        self.kinematics_results: Dict[str, int] = {}
        self.points10_data: List[Dict] = []
        self.grab_side: Optional[str] = None
    
    def reset(self):
        self.mode = None
        self.step = 0
        self.kinematics_results = {}
        self.points10_data = []
        self.grab_side = None


class Calibration:
    VERSION = "2.1"
    
    def __init__(self, filepath: str = 'bookcabinet/calibration.json'):
        self.filepath = filepath
        self.data = self._load()
        self.wizard = CalibrationWizard()
    
    def _default_data(self) -> Dict[str, Any]:
        return {
            'version': self.VERSION,
            'timestamp': datetime.now().isoformat(),
            'kinematics': {
                'x_plus_dir_a': 1,
                'x_plus_dir_b': -1,
                'y_plus_dir_a': 1,
                'y_plus_dir_b': 1,
            },
            'positions': {
                'x': [1891, 6392, 10894],
                'y': [i * 423 for i in range(21)],
            },
            'window': CABINET.get('window', {'col': 1, 'y_start': 7, 'y_end': 11}),
            'grab_front': {
                'extend1': 1900,
                'retract': 1500,
                'extend2': 3100,
            },
            'grab_back': {
                'extend1': 1900,
                'retract': 1500,
                'extend2': 3100,
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
            'tray': {
                'extend_steps': 5000,
                'retract_steps': 5000,
            },
            'blocked_cells': {
                'front': {
                    '1': [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
                },
                'back': {
                    '0': [19, 20],
                    '1': [19, 20],
                    '2': [20],
                },
            },
        }
    
    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    if 'version' not in data:
                        data['version'] = self.VERSION
                    if 'timestamp' not in data:
                        data['timestamp'] = datetime.now().isoformat()
                    if 'blocked_cells' not in data:
                        data['blocked_cells'] = self._default_data()['blocked_cells']
                    if 'tray' not in data:
                        data['tray'] = self._default_data()['tray']
                    return data
            except:
                pass
        return self._default_data()
    
    def save(self):
        self.data['timestamp'] = datetime.now().isoformat()
        self.data['version'] = self.VERSION
        os.makedirs(os.path.dirname(self.filepath) if os.path.dirname(self.filepath) else '.', exist_ok=True)
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
    
    def export_json(self) -> str:
        return json.dumps(self.data, indent=2)
    
    def import_json(self, json_str: str) -> Dict:
        try:
            data = json.loads(json_str)
            validation = self.validate(data)
            if validation['valid']:
                self.data = data
                self.save()
                return {'success': True}
            return {'success': False, 'errors': validation['errors']}
        except json.JSONDecodeError as e:
            return {'success': False, 'errors': [f'Invalid JSON: {str(e)}']}
    
    def toggle_blocked_cell(self, side: str, col: int, row: int) -> bool:
        if 'blocked_cells' not in self.data:
            self.data['blocked_cells'] = {'front': {}, 'back': {}}
        
        if side not in self.data['blocked_cells']:
            self.data['blocked_cells'][side] = {}
        
        col_str = str(col)
        if col_str not in self.data['blocked_cells'][side]:
            self.data['blocked_cells'][side][col_str] = []
        
        cells = self.data['blocked_cells'][side][col_str]
        if row in cells:
            cells.remove(row)
            blocked = False
        else:
            cells.append(row)
            cells.sort()
            blocked = True
        
        self.save()
        return blocked
    
    def is_cell_blocked(self, side: str, col: int, row: int) -> bool:
        blocked = self.data.get('blocked_cells', {}).get(side, {}).get(str(col), [])
        return row in blocked
    
    def validate(self, data: Dict = None) -> Dict:
        """Валидация данных калибровки"""
        to_validate = data if data else self.data
        errors = []
        warnings = []
        
        positions = to_validate.get('positions', {})
        
        x_positions = positions.get('x', [])
        if len(x_positions) != 3:
            errors.append(f'positions.x должен содержать 3 элемента, найдено {len(x_positions)}')
        else:
            for i, x in enumerate(x_positions):
                if not isinstance(x, (int, float)) or x < 0:
                    errors.append(f'positions.x[{i}] должен быть >= 0')
                if x > 15000:
                    warnings.append(f'positions.x[{i}] = {x} выходит за типичный диапазон')
            
            if x_positions != sorted(x_positions):
                errors.append('positions.x должны быть отсортированы по возрастанию')
        
        y_positions = positions.get('y', [])
        if len(y_positions) != 21:
            errors.append(f'positions.y должен содержать 21 элемент, найдено {len(y_positions)}')
        else:
            for i, y in enumerate(y_positions):
                if not isinstance(y, (int, float)) or y < 0:
                    errors.append(f'positions.y[{i}] должен быть >= 0')
            
            if y_positions != sorted(y_positions):
                errors.append('positions.y должны быть отсортированы по возрастанию')
        
        kinematics = to_validate.get('kinematics', {})
        for key in ['x_plus_dir_a', 'x_plus_dir_b', 'y_plus_dir_a', 'y_plus_dir_b']:
            val = kinematics.get(key)
            if val not in [-1, 1]:
                errors.append(f'kinematics.{key} должен быть -1 или 1')
        
        speeds = to_validate.get('speeds', {})
        if speeds.get('xy', 0) <= 0 or speeds.get('xy', 0) > 10000:
            errors.append('speeds.xy должен быть в диапазоне 1-10000')
        if speeds.get('tray', 0) <= 0 or speeds.get('tray', 0) > 10000:
            errors.append('speeds.tray должен быть в диапазоне 1-10000')
        if speeds.get('acceleration', 0) <= 0 or speeds.get('acceleration', 0) > 20000:
            errors.append('speeds.acceleration должен быть в диапазоне 1-20000')
        
        servos = to_validate.get('servos', {})
        for key in ['lock1_open', 'lock1_close', 'lock2_open', 'lock2_close']:
            val = servos.get(key, -1)
            if not isinstance(val, (int, float)) or val < 0 or val > 180:
                errors.append(f'servos.{key} должен быть в диапазоне 0-180')
        
        for grab_key in ['grab_front', 'grab_back']:
            grab = to_validate.get(grab_key)
            if grab is None:
                errors.append(f'{grab_key} обязателен')
                continue
            if not isinstance(grab, dict):
                errors.append(f'{grab_key} должен быть объектом')
                continue
            for key in ['extend1', 'retract', 'extend2']:
                if key not in grab:
                    errors.append(f'{grab_key}.{key} обязателен')
                    continue
                val = grab.get(key, -1)
                if not isinstance(val, (int, float)) or val < 0 or val > 10000:
                    errors.append(f'{grab_key}.{key} должен быть в диапазоне 0-10000')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
        }
    
    def update_with_validation(self, data: Dict) -> Dict:
        """Обновление калибровки с валидацией"""
        merged = {**self.data}
        
        for key in ['positions', 'kinematics', 'speeds', 'servos', 'grab_front', 'grab_back', 'tray', 'blocked_cells']:
            if key in data:
                if isinstance(data[key], dict) and isinstance(merged.get(key), dict):
                    merged[key] = {**merged.get(key, {}), **data[key]}
                else:
                    merged[key] = data[key]
        
        validation = self.validate(merged)
        
        if validation['valid']:
            self.data = merged
            self.save()
            return {'success': True, 'warnings': validation['warnings']}
        else:
            return {'success': False, 'errors': validation['errors'], 'warnings': validation['warnings']}


calibration = Calibration()
