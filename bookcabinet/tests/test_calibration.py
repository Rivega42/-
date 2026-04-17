"""
Tests for tools/calibration.py resolve_cell() function.
"""
import os
import sys
import unittest

# Allow imports from tools/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))

from calibration import resolve_cell  # noqa: E402


class TestResolveCell(unittest.TestCase):
    def test_resolve_window(self):
        """Window cell resolves to positive coordinates."""
        x, y = resolve_cell("1.2.9")
        self.assertGreater(x, 0)
        self.assertGreater(y, 0)

    def test_resolve_disabled_raises(self):
        """Disabled cells raise ValueError."""
        with self.assertRaises(ValueError):
            resolve_cell("1.1.0")

    def test_resolve_invalid_format(self):
        """Invalid address format raises ValueError or KeyError."""
        with self.assertRaises((ValueError, KeyError)):
            resolve_cell("invalid")

    def test_resolve_returns_tuple_of_ints(self):
        """resolve_cell returns an (int, int) tuple."""
        x, y = resolve_cell("1.2.9")
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)


if __name__ == '__main__':
    unittest.main()
