
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock
from collections.abc import Iterator

from pyforge.domain.schedule import (
    OccurrenceStatus,
    Schedule,
    ScheduleOccurrence,
    ensure_utc,
)
from pyforge.exceptions import ScheduleNotFoundError
from pyforge.storage.schedule_repository import ScheduleRepository


def _dt(value: datetime) -> str:
    return ensure_utc(value).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return ensure_utc(parsed)


class SQLiteScheduleRepository(ScheduleRepository):
    def __init__(self, db_path: str | Path = "pyforge.db") -> None:
        self.db_path = str(db_path)
        self._lock = RLock()
        self._memory_connection: sqlite3.Connection | None = None

        if self.db_path == ":memory:":
            self._memory_connection = self._new_connection()
        else:
            Path(self.db_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        self._initialize_schema()

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
            check_same_thread=self.db_path != ":memory:",
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            with self._lock:
                yield self._memory_connection
            return

        connection = self._new_connection()
        try:
            yield connection
        finally:
            connection.close()

    def _initialize_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    interval_seconds REAL NOT NULL
                        CHECK (interval_seconds > 0),
                    next_run_at TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    missed_runs INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS
                    idx_schedules_due
                ON schedules(enabled, next_run_at);

                CREATE TABLE IF NOT EXISTS schedule_occurrences (
                    id TEXT PRIMARY KEY,
                    schedule_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error TEXT,
                    UNIQUE(schedule_id, scheduled_for)
                );

                CREATE INDEX IF NOT EXISTS
                    idx_occurrences_schedule
                ON schedule_occurrences(schedule_id, scheduled_for);
                """
            )

    @staticmethod
    def _schedule_from_row(row: sqlite3.Row) -> Schedule:
        return Schedule(
            id=row["id"],
            job_id=row["job_id"],
            interval_seconds=row["interval_seconds"],
            next_run_at=_parse_dt(row["next_run_at"]),
            enabled=bool(row["enabled"]),
            created_at=_parse_dt(row["created_at"]),
            last_run_at=_parse_dt(row["last_run_at"]),
            missed_runs=row["missed_runs"],
        )

    @staticmethod
    def _occurrence_from_row(
        row: sqlite3.Row,
    ) -> ScheduleOccurrence:
        return ScheduleOccurrence(
            id=row["id"],
            schedule_id=row["schedule_id"],
            job_id=row["job_id"],
            scheduled_for=_parse_dt(row["scheduled_for"]),
            status=OccurrenceStatus(row["status"]),
            started_at=_parse_dt(row["started_at"]),
            finished_at=_parse_dt(row["finished_at"]),
            error=row["error"],
        )

    def create_schedule(self, schedule: Schedule) -> None:
        with self._connection() as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO schedules (
                        id, job_id, interval_seconds,
                        next_run_at, enabled, created_at,
                        last_run_at, missed_runs
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schedule.id,
                        schedule.job_id,
                        schedule.interval_seconds,
                        _dt(schedule.next_run_at),
                        int(schedule.enabled),
                        _dt(schedule.created_at),
                        _dt(schedule.last_run_at)
                        if schedule.last_run_at else None,
                        schedule.missed_runs,
                    ),
                )

    def get_schedule(self, schedule_id: str) -> Schedule:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM schedules WHERE id = ?",
                (schedule_id,),
            ).fetchone()

        if row is None:
            raise ScheduleNotFoundError(
                f"Schedule not found: {schedule_id}"
            )
        return self._schedule_from_row(row)

    def list_schedules(self) -> list[Schedule]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM schedules ORDER BY created_at, id"
            ).fetchall()

        return [self._schedule_from_row(row) for row in rows]

    def delete_schedule(self, schedule_id: str) -> None:
        with self._connection() as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM schedules WHERE id = ?",
                    (schedule_id,),
                )
                if cursor.rowcount == 0:
                    raise ScheduleNotFoundError(
                        f"Schedule not found: {schedule_id}"
                    )

    def set_enabled(
        self,
        schedule_id: str,
        enabled: bool,
        now: datetime,
    ) -> Schedule:
        now = ensure_utc(now)

        with self._connection() as connection:
            with connection:
                row = connection.execute(
                    "SELECT * FROM schedules WHERE id = ?",
                    (schedule_id,),
                ).fetchone()

                if row is None:
                    raise ScheduleNotFoundError(
                        f"Schedule not found: {schedule_id}"
                    )

                next_run = _parse_dt(row["next_run_at"])
                interval = row["interval_seconds"]

                # Re-enabling a stale schedule starts a fresh interval.
                if enabled and next_run <= now:
                    next_run = now + timedelta(seconds=interval)

                connection.execute(
                    """
                    UPDATE schedules
                    SET enabled = ?, next_run_at = ?
                    WHERE id = ?
                    """,
                    (int(enabled), _dt(next_run), schedule_id),
                )

        return self.get_schedule(schedule_id)

    def claim_due(
        self,
        now: datetime,
        grace_seconds: float,
        excluded_schedule_ids: set[str],
    ) -> list[ScheduleOccurrence]:
        now = ensure_utc(now)

        if grace_seconds < 0:
            raise ValueError("grace_seconds cannot be negative")

        claimed: list[ScheduleOccurrence] = []

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """
                    SELECT * FROM schedules
                    WHERE enabled = 1 AND next_run_at <= ?
                    ORDER BY next_run_at, id
                    """,
                    (_dt(now),),
                ).fetchall()

                for row in rows:
                    schedule = self._schedule_from_row(row)
                    due_at = schedule.next_run_at

                    elapsed = max(
                        0.0, (now - due_at).total_seconds()
                    )
                    due_count = (
                        int(elapsed // schedule.interval_seconds) + 1
                    )
                    next_run = due_at + timedelta(
                        seconds=due_count * schedule.interval_seconds
                    )

                    # All overdue occurrences are skipped while
                    # this schedule already has work in flight.
                    if schedule.id in excluded_schedule_ids:
                        connection.execute(
                            """
                            UPDATE schedules
                            SET next_run_at = ?,
                                missed_runs = missed_runs + ?
                            WHERE id = ?
                            """,
                            (_dt(next_run), due_count, schedule.id),
                        )
                        continue

                    if elapsed > grace_seconds:
                        connection.execute(
                            """
                            UPDATE schedules
                            SET next_run_at = ?,
                                missed_runs = missed_runs + ?
                            WHERE id = ?
                            """,
                            (_dt(next_run), due_count, schedule.id),
                        )
                        continue

                    occurrence = ScheduleOccurrence(
                        schedule_id=schedule.id,
                        job_id=schedule.job_id,
                        scheduled_for=due_at,
                    )

                    cursor = connection.execute(
                        """
                        INSERT OR IGNORE INTO schedule_occurrences (
                            id, schedule_id, job_id, scheduled_for,
                            status, started_at, finished_at, error
                        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
                        """,
                        (
                            occurrence.id,
                            occurrence.schedule_id,
                            occurrence.job_id,
                            _dt(occurrence.scheduled_for),
                            occurrence.status.value,
                        ),
                    )

                    # Advance cadence and account for any additional
                    # occurrences that elapsed while we were offline.
                    connection.execute(
                        """
                        UPDATE schedules
                        SET next_run_at = ?,
                            missed_runs = missed_runs + ?
                        WHERE id = ?
                        """,
                        (
                            _dt(next_run),
                            due_count - 1,
                            schedule.id,
                        ),
                    )

                    if cursor.rowcount == 1:
                        claimed.append(occurrence)

                connection.commit()
            except Exception:
                connection.rollback()
                raise

        return claimed

    def mark_running(
        self,
        occurrence_id: str,
        started_at: datetime,
    ) -> None:
        with self._connection() as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE schedule_occurrences
                    SET status = ?, started_at = ?
                    WHERE id = ? AND status = ?
                    """,
                    (
                        OccurrenceStatus.RUNNING.value,
                        _dt(started_at),
                        occurrence_id,
                        OccurrenceStatus.CLAIMED.value,
                    ),
                )
                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Occurrence cannot start: {occurrence_id}"
                    )

    def finish_occurrence(
        self,
        occurrence_id: str,
        status: str,
        finished_at: datetime,
        error: str | None = None,
    ) -> None:
        allowed = {
            OccurrenceStatus.SUCCESS.value,
            OccurrenceStatus.FAILED.value,
            OccurrenceStatus.INTERRUPTED.value,
        }
        if status not in allowed:
            raise ValueError(f"Invalid final status: {status}")

        finished_at = ensure_utc(finished_at)

        with self._connection() as connection:
            with connection:
                row = connection.execute(
                    """
                    SELECT schedule_id FROM schedule_occurrences
                    WHERE id = ? AND status IN (?, ?)
                    """,
                    (
                        occurrence_id,
                        OccurrenceStatus.CLAIMED.value,
                        OccurrenceStatus.RUNNING.value,
                    ),
                ).fetchone()

                if row is None:
                    raise ValueError(
                        f"Occurrence cannot finish: {occurrence_id}"
                    )

                connection.execute(
                    """
                    UPDATE schedule_occurrences
                    SET status = ?, finished_at = ?, error = ?
                    WHERE id = ?
                    """,
                    (status, _dt(finished_at), error, occurrence_id),
                )
                connection.execute(
                    """
                    UPDATE schedules SET last_run_at = ?
                    WHERE id = ?
                    """,
                    (_dt(finished_at), row["schedule_id"]),
                )

    def list_occurrences(
        self,
        schedule_id: str,
    ) -> list[ScheduleOccurrence]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM schedule_occurrences
                WHERE schedule_id = ?
                ORDER BY scheduled_for DESC
                """,
                (schedule_id,),
            ).fetchall()

        return [self._occurrence_from_row(row) for row in rows]

    def recover_incomplete(self, now: datetime) -> int:
        now = ensure_utc(now)

        with self._connection() as connection:
            with connection:
                rows = connection.execute(
                    """
                    SELECT id, schedule_id FROM schedule_occurrences
                    WHERE status IN (?, ?)
                    """,
                    (
                        OccurrenceStatus.CLAIMED.value,
                        OccurrenceStatus.RUNNING.value,
                    ),
                ).fetchall()

                for row in rows:
                    connection.execute(
                        """
                        UPDATE schedule_occurrences
                        SET status = ?, finished_at = ?,
                            error = ?
                        WHERE id = ?
                        """,
                        (
                            OccurrenceStatus.INTERRUPTED.value,
                            _dt(now),
                            "Interrupted by scheduler restart",
                            row["id"],
                        ),
                    )
                    connection.execute(
                        """
                        UPDATE schedules SET last_run_at = ?
                        WHERE id = ?
                        """,
                        (_dt(now), row["schedule_id"]),
                    )

        return len(rows)
