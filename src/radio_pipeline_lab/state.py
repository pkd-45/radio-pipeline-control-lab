from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StageRecord:
    run_id: str
    stage: str
    attempt: int
    status: str
    started_at: str
    finished_at: str | None
    detail: dict[str, Any]


class RunStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS stage_attempts (
                    run_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    detail_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, stage, attempt)
                )
                """
            )

    def start(self, run_id: str, stage: str, attempt: int) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO stage_attempts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, stage, attempt, "RUNNING", now, None, "{}"),
            )

    def finish(
        self, run_id: str, stage: str, attempt: int, status: str, detail: dict[str, Any]
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE stage_attempts
                SET status = ?, finished_at = ?, detail_json = ?
                WHERE run_id = ? AND stage = ? AND attempt = ?
                """,
                (status, now, json.dumps(detail, sort_keys=True), run_id, stage, attempt),
            )

    def latest(self, run_id: str, stage: str) -> StageRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, stage, attempt, status, started_at, finished_at, detail_json
                FROM stage_attempts
                WHERE run_id = ? AND stage = ?
                ORDER BY attempt DESC LIMIT 1
                """,
                (run_id, stage),
            ).fetchone()
        return None if row is None else self._record(row)

    def records(self, run_id: str) -> list[StageRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, stage, attempt, status, started_at, finished_at, detail_json
                FROM stage_attempts WHERE run_id = ? ORDER BY rowid
                """,
                (run_id,),
            ).fetchall()
        return [self._record(row) for row in rows]

    @staticmethod
    def _record(row: tuple[Any, ...]) -> StageRecord:
        return StageRecord(
            run_id=str(row[0]),
            stage=str(row[1]),
            attempt=int(row[2]),
            status=str(row[3]),
            started_at=str(row[4]),
            finished_at=None if row[5] is None else str(row[5]),
            detail=json.loads(str(row[6])),
        )
