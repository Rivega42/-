"""
BookCabinet calibration module.
Provides cell address -> (x, y) coordinate resolution via piecewise linear interpolation.

Address format: depth.rack.shelf
  depth: 1=front, 2=back
  rack:  1, 2, 3
  shelf: 0-20 (21 is disabled)

Per-rack Y anchors:
  calibration.json теперь хранит anchors отдельно для каждой стойки:
    shelves.rack_y_anchors.1 = [{shelf, front_y, back_y}, ...]
    shelves.rack_y_anchors.2 = [...]
    shelves.rack_y_anchors.3 = [...]
  Если для стойки нет своих анкоров — используются общие shelves.anchors (совместимость).
"""
import json
import os
from typing import Tuple

_CAL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'calibration.json')

def _load() -> dict:
    with open(_CAL_PATH, 'r') as f:
        return json.load(f)

def get_rack_x(rack: int, cal: dict) -> int:
    """Return X position for given rack (1-3)."""
    return cal['racks'][str(rack)]

def _get_anchors_for_rack(rack: int, cal: dict) -> list:
    """
    Возвращает анкоры для конкретной стойки.
    Если есть rack_y_anchors[rack] — берём их.
    Иначе — общие anchors (обратная совместимость).
    """
    rack_y = cal['shelves'].get('rack_y_anchors', {})
    if str(rack) in rack_y and rack_y[str(rack)]:
        return rack_y[str(rack)]
    return cal['shelves']['anchors']

def interpolate_y(shelf: int, depth: int, cal: dict, rack: int = 1) -> int:
    """
    Interpolate Y position for given shelf, depth and rack using piecewise linear method.
    depth: 1=front, 2=back
    rack: 1, 2, 3 (per-rack anchors если есть)
    """
    anchors = _get_anchors_for_rack(rack, cal)
    key = 'front_y' if depth == 1 else 'back_y'

    lower = None
    upper = None
    for a in anchors:
        if a['shelf'] <= shelf:
            lower = a
        if a['shelf'] >= shelf and upper is None:
            upper = a

    if lower is None:
        return upper[key]
    if upper is None:
        return lower[key]
    if lower['shelf'] == upper['shelf']:
        return lower[key]

    t = (shelf - lower['shelf']) / (upper['shelf'] - lower['shelf'])
    y = lower[key] + t * (upper[key] - lower[key])
    return int(round(y))

def resolve_cell(address: str) -> Tuple[int, int]:
    """
    Resolve cell address to (x, y) coordinates.

    Args:
        address: Cell address in format 'depth.rack.shelf' (e.g. '1.2.9')

    Returns:
        (x, y) tuple in steps

    Raises:
        ValueError: If cell is disabled or address is invalid
    """
    cal = _load()

    parts = address.split('.')
    if len(parts) != 3:
        raise ValueError(f'Invalid address format: {address}. Expected depth.rack.shelf')

    depth, rack, shelf = int(parts[0]), int(parts[1]), int(parts[2])

    if address in cal.get('disabled_cells', []):
        raise ValueError(f'Cell {address} is disabled')

    x = get_rack_x(rack, cal)
    y = interpolate_y(shelf, depth, cal, rack=rack)  # передаём rack!

    return x, y

def list_disabled() -> list:
    """Return list of disabled cell addresses."""
    return _load().get('disabled_cells', [])

def get_window() -> str:
    """Return window cell address."""
    return _load()['special_cells']['window']

if __name__ == '__main__':
    test_cells = ['1.1.5', '1.2.5', '1.3.5', '1.1.1', '1.2.1', '1.3.1',
                  '1.1.10', '1.2.10', '1.3.10']
    print('Cell resolution test (per-rack):')
    print(f'  {"Address":<12} {"X":>8} {"Y":>8}')
    print('  ' + '-' * 35)
    for addr in test_cells:
        try:
            x, y = resolve_cell(addr)
            print(f'  {addr:<12} {x:>8} {y:>8}')
        except ValueError as e:
            print(f'  {addr:<12} DISABLED')
