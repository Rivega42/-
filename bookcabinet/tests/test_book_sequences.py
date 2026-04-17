"""
Tests for BookSequenceRunner — issue/return rejection paths.

These tests avoid real hardware by mocking pigpio and the motion/tray
controllers, then exercising only the validation logic.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import asyncio
import pytest

# Allow imports from tools/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))


def _make_runner():
    """Create a BookSequenceRunner with pigpio fully mocked."""
    import pigpio

    fake_pi = MagicMock()
    fake_pi.connected = True

    with patch.object(pigpio, 'pi', return_value=fake_pi):
        from book_sequences import BookSequenceRunner
        runner = BookSequenceRunner(pi=fake_pi)
    return runner


@pytest.mark.asyncio
async def test_issue_rejects_disabled_cell():
    """Issue sequence rejects disabled cells early (closes #61)."""
    runner = _make_runner()
    result = await runner.issue_book_sequence("1.1.0")  # known disabled
    assert result['success'] is False
    assert 'недоступна' in result['error'] or 'disabled' in result['error'].lower()


@pytest.mark.asyncio
async def test_issue_rejects_invalid_address_format():
    """Invalid address format should fail fast with clear error."""
    runner = _make_runner()
    result = await runner.issue_book_sequence("not-a-cell")
    assert result['success'] is False
    assert result['error']


@pytest.mark.asyncio
async def test_concurrent_issue_rejected():
    """Second issue rejected while first running (closes #44)."""
    from book_sequences import BookSequenceRunner

    r1 = _make_runner()
    r2 = _make_runner()
    # Lock class-level — shared across instances
    async with BookSequenceRunner._global_lock:
        result = await r2.issue_book_sequence("1.1.5")
        assert result['success'] is False
        assert 'выполняется' in result['error'] or 'busy' in result['error'].lower()


if __name__ == '__main__':
    # Allow `python test_book_sequences.py` for quick smoke
    import unittest
    unittest.main()
