"""
Tests for BookSequenceRunner — issue/return rejection paths.

Pigpio is installed only on the real Pi, so these tests stub it out at
sys.modules level before importing book_sequences. We only exercise the
validation logic (disabled cell, invalid format, concurrent lock) —
no hardware calls are made.

Uses unittest.IsolatedAsyncioTestCase so pytest-asyncio is not required.
"""
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

# Allow imports from tools/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))


def _install_pigpio_stub():
    """Install a fake `pigpio` module so book_sequences can be imported."""
    if 'pigpio' in sys.modules:
        return
    fake_module = types.ModuleType('pigpio')

    class _FakePi:
        def __init__(self, *args, **kwargs):
            self.connected = True

        def __getattr__(self, name):
            return MagicMock()

    fake_module.pi = _FakePi  # type: ignore[attr-defined]
    fake_module.OUTPUT = 1  # type: ignore[attr-defined]
    fake_module.INPUT = 0  # type: ignore[attr-defined]
    fake_module.PUD_OFF = 0  # type: ignore[attr-defined]
    fake_module.PUD_UP = 2  # type: ignore[attr-defined]
    fake_module.FALLING_EDGE = 1  # type: ignore[attr-defined]
    sys.modules['pigpio'] = fake_module


def _make_runner():
    """Create a BookSequenceRunner with pigpio stubbed and pi mocked."""
    _install_pigpio_stub()
    from book_sequences import BookSequenceRunner  # imported lazily
    fake_pi = MagicMock()
    fake_pi.connected = True
    return BookSequenceRunner(pi=fake_pi)


class TestIssueRejection(unittest.IsolatedAsyncioTestCase):
    """Cover early-validation / concurrency guards in issue_book_sequence."""

    async def test_issue_rejects_disabled_cell(self):
        """Issue sequence rejects disabled cells early (closes #61)."""
        runner = _make_runner()
        result = await runner.issue_book_sequence("1.1.0")  # known disabled
        self.assertFalse(result['success'])
        self.assertTrue(
            'недоступна' in result['error'] or 'disabled' in result['error'].lower(),
            f"unexpected error: {result['error']}",
        )

    async def test_issue_rejects_invalid_address_format(self):
        """Invalid address format fails fast with clear error."""
        runner = _make_runner()
        result = await runner.issue_book_sequence("not-a-cell")
        self.assertFalse(result['success'])
        self.assertTrue(result['error'])

    async def test_concurrent_issue_rejected(self):
        """Second issue rejected while first running (closes #44)."""
        _install_pigpio_stub()
        from book_sequences import BookSequenceRunner

        r2 = _make_runner()
        # Lock class-level — shared across instances
        async with BookSequenceRunner._global_lock:
            result = await r2.issue_book_sequence("1.1.5")
            self.assertFalse(result['success'])
            self.assertTrue(
                'выполняется' in result['error'] or 'busy' in result['error'].lower(),
                f"unexpected error: {result['error']}",
            )


if __name__ == '__main__':
    unittest.main()
