
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult
from pyforge.exceptions import JobNotFoundError, JobResultNotFoundError
from pyforge.storage.repository import JobRepository


class SQLiteRepository(JobRepository):
    def __init__(self, db_path: str | Path = "pyforge.db") -> None:
        self.db_path = str(db_path)

        # Keep one connection alive for an in-memory database.
        self._memory_connection = None

        if self.db_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:")
        else:
            # Create the parent directory if it does not exist.
            Path(self.db_path).parent.mkdir(
                parents=True, exist_ok=True
            )

        # Create the tables automatically.
        self._initialize_schema()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        # Each file-based operation gets its own connection.
        connection = (
            self._memory_connection
            if self._memory_connection is not None
            else sqlite3.connect(self.db_path, timeout=30)
        )

        should_close = self._memory_connection is None

        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")

            # Commit on success; roll back on an exception.
            with connection:
                yield connection
        finally:
            if should_close:
                connection.close()

    def _initialize_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    timeout REAL,
                    metadata_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS job_results (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    stdout TEXT NOT NULL,
                    stderr TEXT NOT NULL,
                    exit_code INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    error TEXT,
                    FOREIGN KEY (job_id)
                        REFERENCES jobs(id)
                        ON DELETE CASCADE
                );
                """
            )

    def save_job(self, job: Job) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, name, command_json, status,
                    created_at, timeout, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    command_json = excluded.command_json,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    timeout = excluded.timeout,
                    metadata_json = excluded.metadata_json
                """,
                (
                    job.id,
                    job.name,
                    json.dumps(job.command),
                    job.status.value,
                    job.created_at.isoformat(),
                    job.timeout,
                    json.dumps(job.metadata),
                ),
            )

    def get_job(self, job_id: str) -> Job:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            raise JobNotFoundError(
                f"Job '{job_id}' was not found"
            )

        return self._row_to_job(row)

    def list_jobs(self) -> list[Job]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at, id"
            ).fetchall()

        return [self._row_to_job(row) for row in rows]

    def delete_job(self, job_id: str) -> None:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM jobs WHERE id = ?",
                (job_id,),
            )

            if cursor.rowcount == 0:
                raise JobNotFoundError(
                    f"Job '{job_id}' was not found"
                )

        # The associated result is deleted automatically through
        # the foreign key's ON DELETE CASCADE rule.

    def save_result(self, result: JobResult) -> None:
        with self._connection() as connection:
            job = connection.execute(
                "SELECT id FROM jobs WHERE id = ?",
                (result.job_id,),
            ).fetchone()

            if job is None:
                raise JobNotFoundError(
                    f"Job '{result.job_id}' was not found"
                )

            connection.execute(
                """
                INSERT INTO job_results (
                    job_id, status, stdout, stderr,
                    exit_code, started_at, finished_at, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    stdout = excluded.stdout,
                    stderr = excluded.stderr,
                    exit_code = excluded.exit_code,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    error = excluded.error
                """,
                (
                    result.job_id,
                    result.status.value,
                    result.stdout,
                    result.stderr,
                    result.exit_code,
                    result.started_at.isoformat(),
                    result.finished_at.isoformat(),
                    result.error,
                ),
            )

    def get_result(self, job_id: str) -> JobResult:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM job_results WHERE job_id = ?",
                (job_id,),
            ).fetchone()

        if row is None:
            raise JobResultNotFoundError(
                f"Result for job '{job_id}' was not found"
            )

        return self._row_to_result(row)

    def list_results(self) -> list[JobResult]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM job_results ORDER BY started_at, job_id"
            ).fetchall()

        return [self._row_to_result(row) for row in rows]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            name=row["name"],
            command=json.loads(row["command_json"]),
            status=JobStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            timeout=row["timeout"],
            metadata=json.loads(row["metadata_json"]),
        )

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> JobResult:
        return JobResult(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            stdout=row["stdout"],
            stderr=row["stderr"],
            exit_code=row["exit_code"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]),
            error=row["error"],
        )
