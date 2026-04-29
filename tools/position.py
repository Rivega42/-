"""
Carriage position persistence.
Saves/loads (x, y) to /tmp/carriage_pos.json.
Import and call save_pos(x, y) from any tool that moves the carriage.
"""
import json
import os

POS_FILE = '/tmp/carriage_pos.json'

def save_pos(x: int, y: int) -> None:
    try:
        with open(POS_FILE, 'w') as f:
            json.dump({'x': x, 'y': y}, f)
    except Exception:
        pass

def load_pos() -> tuple[int, int] | None:
    try:
        if not os.path.exists(POS_FILE):
            return None
        with open(POS_FILE) as f:
            data = json.load(f)
        return (data['x'], data['y'])
    except Exception:
        return None

def clear_pos() -> None:
    try:
        os.remove(POS_FILE)
    except FileNotFoundError:
        pass
