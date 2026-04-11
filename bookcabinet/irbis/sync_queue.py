"""
IRBIS offline sync queue.

When the IRBIS server is unavailable, pending operations (issue / return)
are saved to a JSON file and retried periodically once the connection is
restored.
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger('bookcabinet.irbis.sync_queue')


class IrbisSyncQueue:
    """Queue for IRBIS operations when server is unavailable.

    Saves pending operations to a JSON file.
    Retries periodically when connection is restored.
    """

    def __init__(self, queue_file: str = 'data/irbis_queue.json'):
        self.queue_file = queue_file
        self._queue: List[Dict] = []
        self._sync_task: Optional[asyncio.Task] = None
        self._load()

    # ── persistence ──────────────────────────────────────

    def _ensure_dir(self):
        d = os.path.dirname(self.queue_file)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)

    def _load(self):
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    self._queue = json.load(f)
                logger.info(f"Loaded {len(self._queue)} pending IRBIS operations from {self.queue_file}")
            except Exception as e:
                logger.warning(f"Failed to load IRBIS queue: {e}")
                self._queue = []
        else:
            self._queue = []

    def _save(self):
        self._ensure_dir()
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(self._queue, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save IRBIS queue: {e}")

    # ── public API ───────────────────────────────────────

    def add(self, operation: str, params: dict):
        """Add operation to queue (issue / return)."""
        entry = {
            'id': str(uuid.uuid4()),
            'operation': operation,
            'params': params,
            'added_at': datetime.now().isoformat(),
            'attempts': 0,
            'last_attempt': None,
            'status': 'pending',
            'error': None,
        }
        self._queue.append(entry)
        self._save()
        logger.info(f"Queued IRBIS {operation}: {params}")

    def get_pending(self) -> list:
        """Get all pending operations."""
        return [e for e in self._queue if e['status'] == 'pending']

    def get_all(self) -> list:
        """Get all operations (pending + done + failed)."""
        return list(self._queue)

    async def sync(self) -> dict:
        """Try to process all pending operations.

        Returns dict with counts: {synced, failed, remaining}.
        """
        from .service import library_service

        synced = 0
        failed = 0

        for entry in self._queue:
            if entry['status'] != 'pending':
                continue

            entry['attempts'] += 1
            entry['last_attempt'] = datetime.now().isoformat()

            try:
                op = entry['operation']
                params = entry['params']

                if op == 'issue':
                    success, msg = await library_service.issue_book(
                        params.get('book_rfid', ''),
                        params.get('user_rfid'),
                    )
                elif op == 'return':
                    success, msg = await library_service.return_book(
                        params.get('book_rfid', ''),
                    )
                else:
                    success = False
                    msg = f"Unknown operation: {op}"

                if success:
                    entry['status'] = 'done'
                    synced += 1
                    logger.info(f"Synced IRBIS {op}: {params}")
                else:
                    entry['error'] = msg
                    # Keep as pending for retry unless attempts exceeded
                    if entry['attempts'] >= 10:
                        entry['status'] = 'failed'
                        failed += 1
                        logger.warning(f"IRBIS {op} permanently failed after {entry['attempts']} attempts: {msg}")

            except Exception as e:
                entry['error'] = str(e)
                if entry['attempts'] >= 10:
                    entry['status'] = 'failed'
                    failed += 1
                logger.warning(f"IRBIS sync error for {entry['operation']}: {e}")

        remaining = len(self.get_pending())
        self._save()
        return {'synced': synced, 'failed': failed, 'remaining': remaining}

    # ── periodic background task ─────────────────────────

    async def _periodic_sync(self, interval_seconds: int = 300):
        """Background task that syncs every `interval_seconds` (default 5 min)."""
        while True:
            await asyncio.sleep(interval_seconds)
            pending = self.get_pending()
            if pending:
                logger.info(f"Periodic IRBIS sync: {len(pending)} pending operations")
                try:
                    result = await self.sync()
                    logger.info(f"Periodic sync result: {result}")
                except Exception as e:
                    logger.error(f"Periodic sync error: {e}")

    def start_periodic_sync(self, interval_seconds: int = 300):
        """Start the periodic sync background task."""
        if self._sync_task is None or self._sync_task.done():
            self._sync_task = asyncio.create_task(
                self._periodic_sync(interval_seconds)
            )
            logger.info(f"IRBIS periodic sync started (every {interval_seconds}s)")

    def stop_periodic_sync(self):
        """Stop the periodic sync background task."""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            self._sync_task = None
            logger.info("IRBIS periodic sync stopped")


sync_queue = IrbisSyncQueue()
