"""
CoreXY кинематика с полным расчётом траекторий
"""
from typing import Tuple, List, Dict
from ..config import CABINET
from .calibration import calibration


class CoreXY:
    """Класс для расчёта CoreXY кинематики"""
    
    def __init__(self):
        self.reload_calibration()
    
    def reload_calibration(self):
        """Загрузить калибровочные данные"""
        self.positions_x = calibration.get('positions.x', [0, 4500, 9000])
        self.positions_y = calibration.get('positions.y', [i * 450 for i in range(21)])
        self.kinematics = calibration.get('kinematics', {
            'x_plus_dir_a': 1,
            'x_plus_dir_b': -1,
            'y_plus_dir_a': 1,
            'y_plus_dir_b': 1,
        })
    
    def cell_to_steps(self, row: str, x: int, y: int) -> Tuple[int, int]:
        """Преобразовать координаты ячейки в шаги моторов"""
        steps_x = self.positions_x[x] if x < len(self.positions_x) else 0
        steps_y = self.positions_y[y] if y < len(self.positions_y) else 0
        return (steps_x, steps_y)
    
    def window_position(self) -> Tuple[int, int]:
        """Получить позицию окна выдачи"""
        window = CABINET['window']
        return self.cell_to_steps(window['row'], window['x'], window['y'])
    
    def calculate_ab_steps(self, dx: int, dy: int) -> Tuple[int, int]:
        """Рассчитать шаги для моторов A и B по CoreXY кинематике
        
        CoreXY кинематика:
        - Мотор A вращается в одном направлении -> движение по диагонали
        - Мотор B вращается в одном направлении -> движение по другой диагонали
        - Оба мотора вращаются в одном направлении -> движение по Y
        - Оба мотора вращаются в разных направлениях -> движение по X
        
        Формулы:
        steps_A = dx * dir_a + dy * dir_a
        steps_B = dx * dir_b + dy * dir_b
        """
        kin = self.kinematics
        steps_a = dx * kin['x_plus_dir_a'] + dy * kin['y_plus_dir_a']
        steps_b = dx * kin['x_plus_dir_b'] + dy * kin['y_plus_dir_b']
        return (steps_a, steps_b)
    
    def inverse_kinematics(self, steps_a: int, steps_b: int) -> Tuple[int, int]:
        """Обратная кинематика: шаги моторов -> координаты X, Y"""
        dx = (steps_a - steps_b) // 2
        dy = (steps_a + steps_b) // 2
        return (dx, dy)
    
    def get_all_cell_positions(self) -> List[Dict]:
        """Получить все позиции ячеек для калибровки"""
        positions = []
        for row in CABINET['rows']:
            for x in range(CABINET['columns']):
                for y in range(CABINET['positions']):
                    steps_x, steps_y = self.cell_to_steps(row, x, y)
                    positions.append({
                        'row': row,
                        'x': x,
                        'y': y,
                        'steps_x': steps_x,
                        'steps_y': steps_y,
                    })
        return positions
    
    def estimate_move_time(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], 
                           speed: int = 4000) -> float:
        """Оценка времени перемещения в секундах"""
        dx = abs(to_pos[0] - from_pos[0])
        dy = abs(to_pos[1] - from_pos[1])
        
        distance = max(dx, dy)
        
        if speed <= 0:
            return 0
        return distance / speed
    
    def find_optimal_path(self, start: Tuple[int, int], end: Tuple[int, int], 
                          obstacles: List[Tuple[int, int]] = None) -> List[Tuple[int, int]]:
        """Найти оптимальный путь между точками
        
        Для CoreXY лучше двигаться сначала по одной оси, потом по другой,
        чтобы избежать диагональных движений с разной скоростью осей.
        """
        path = []
        sx, sy = start
        ex, ey = end
        
        path.append((ex, sy))
        
        path.append((ex, ey))
        
        return path


corexy = CoreXY()
