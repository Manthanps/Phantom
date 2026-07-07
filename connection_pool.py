"""Simple connection pool abstraction.

For SQLite, pool_size=1 is the recommended default; WAL mode already handles
concurrent reads. This module is designed so replacing SQLite with Postgres
requires only swapping the connection factory.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue


class ConnectionPool:
    """Queue-backed pool of SQLite connections.

    Connections are acquired with `acquire()` and returned automatically
    on context manager exit.
    """

    def __init__(self, db_path: str | Path, pool_size: int = 1) -> None:
        self._db_path = str(db_path)
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self._pool.put(self._make_connection())

    # ── Public ─────────────────────────────────────────────────────────────────

    @contextmanager
    def acquire(self):
        conn = self._pool.get(timeout=5)
        try:
            yield conn
        finally:
            self._pool.put(conn)

    def close_all(self) -> None:
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break

    @property
    def size(self) -> int:
        return self._pool.qsize()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _make_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
