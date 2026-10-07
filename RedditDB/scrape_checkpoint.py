"""Durable scrape checkpoints for incremental Reddit pulls (#10)."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Checkpoint:
    subreddit: str
    last_fullname: str
    fetched_at: str


class CheckpointStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS scrape_checkpoints (
                    subreddit TEXT PRIMARY KEY,
                    last_fullname TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )"""
            )

    def get(self, subreddit: str) -> Checkpoint | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT subreddit, last_fullname, fetched_at FROM scrape_checkpoints WHERE subreddit=?",
                (subreddit,),
            ).fetchone()
        if not row:
            return None
        return Checkpoint(**dict(row))

    def set(self, subreddit: str, last_fullname: str) -> Checkpoint:
        cp = Checkpoint(
            subreddit=subreddit,
            last_fullname=last_fullname,
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO scrape_checkpoints(subreddit, last_fullname, fetched_at)
                   VALUES(?,?,?)
                   ON CONFLICT(subreddit) DO UPDATE SET
                     last_fullname=excluded.last_fullname,
                     fetched_at=excluded.fetched_at""",
                (cp.subreddit, cp.last_fullname, cp.fetched_at),
            )
        return cp

    def should_skip(self, subreddit: str, fullname: str, *, full: bool = False) -> bool:
        if full or not fullname:
            return False
        cp = self.get(subreddit)
        if cp is None:
            return False
        # Reddit fullnames are like t3_abc; lexicographic works for same prefix type
        return fullname <= cp.last_fullname
