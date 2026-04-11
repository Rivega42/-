"""
BookCabinet calibration module.
Provides cell address -> (x, y) coordinate resolution via piecewise linear interpolation.

Address format: depth.rack.shelf
  depth: 1=front, 2=back
  rack:  1, 2, 3
  shelf: 0-20 (21 is disabled)
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

def interpolate_y(shelf: int, depth: int, cal: dict) -> int:
    """
    Interpolate Y position for given shelf and depth using piecewise linear method.
    depth: 1=front, 2=back
    """
    anchors = cal['shelves']['anchors']
    key = 'front_y' if depth == 1 else 'back_y'

    # Find surrounding anchors
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

    # Linear interpolation
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
    y = interpolate_y(shelf, depth, cal)
    
    return x, y

def list_disabled() -> list:
    """Return list of disabled cell addresses."""
    return _load().get('disabled_cells', [])

def get_window() -> str:
    """Return window cell address."""
    return _load()['special_cells']['window']

if __name__ == '__main__':
    # Quick test
    test_cells = ['1.2.0', '1.2.9', '2.2.9', '1.1.14', '2.3.18', '1.2.5', '2.2.21']
    print('Cell resolution test:')
    print(f'  {"Address":<12} {"X":>8} {"Y":>8}  Status')
    print('  ' + '-' * 40)
    for addr in test_cells:
        try:
            x, y = resolve_cell(addr)
            marker = ' <- WINDOW' if addr == get_window() else ''
            print(f'  {addr:<12} {x:>8} {y:>8}{marker}')
        except ValueError as e:
            print(f'  {addr:<12} {"DISABLED":>18}')
