"""Thread-safe SQLite connection manager with WAL mode and pragma setup."""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SQLiteManager:
    """Manages a single persistent SQLite connection guarded by a reentrant lock.

    WAL mode allows concurrent reads while a single writer holds the lock.
    All write paths go through `transaction()` which guarantees commit/rollback.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()  # RLock allows re-entry from same thread

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def connect(self) -> None:
        with self._lock:
            if self._conn is not None:
                return
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._apply_pragmas()
            logger.debug("SQLite connected: %s", self._db_path)

    def close(self) -> None:
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                logger.debug("SQLite connection closed")

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    # ── Read API ───────────────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a SQL statement and return the cursor (reads or single writes)."""
        with self._lock:
            assert self._conn is not None, "Call connect() first"
            return self._conn.execute(sql, params)

    # ── Write API ─────────────────────────────────────────────────────────────

    @contextmanager
    def transaction(self):
        """Context manager that commits on success and rolls back on exception."""
        with self._lock:
            assert self._conn is not None, "Call connect() first"
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # ── Internal ───────────────────────────────────────────────────────────────

    def _apply_pragmas(self) -> None:
        assert self._conn is not None
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.commit()
        logger.debug("SQLite pragmas applied (WAL, FK=ON, NORMAL sync)")
