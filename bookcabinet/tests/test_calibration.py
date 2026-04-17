"""
Tests for tools/calibration.py resolve_cell() function.
"""
import os
import sys

import pytest

# Allow imports from tools/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

from calibration import resolve_cell  # noqa: E402


def test_resolve_window():
    """Window cell resolves to positive coordinates."""
    x, y = resolve_cell("1.2.9")
    assert x > 0 and y > 0


def test_resolve_disabled_raises():
    """Disabled cells raise ValueError."""
    with pytest.raises(ValueError):
        resolve_cell("1.1.0")


def test_resolve_invalid_format():
    """Invalid address format raises ValueError or KeyError."""
    with pytest.raises((ValueError, KeyError)):
        resolve_cell("invalid")


def test_resolve_returns_tuple_of_ints():
    """resolve_cell returns a (int, int) tuple."""
    x, y = resolve_cell("1.2.9")
    assert isinstance(x, int)
    assert isinstance(y, int)
