from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from uuid import uuid4


class OccurrenceStatus(Enum):
    CLAIMED = "claimed"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """Reject naive datetimes and normalize aware datetimes to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime must be timezone-aware")

    return value.astimezone(timezone.utc)


@dataclass
class Schedule:
    job_id: str
    interval_seconds: float
    next_run_at: datetime
    id: str = field(default_factory=lambda: str(uuid4()))
    enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)
    last_run_at: datetime | None = None
    missed_runs: int = 0

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must not be empty")

        if (
            not isfinite(self.interval_seconds)
            or self.interval_seconds <= 0
        ):
            raise ValueError("interval_seconds must be positive and finite")

        if self.missed_runs < 0:
            raise ValueError("missed_runs must be non-negative")

        self.next_run_at = ensure_utc(self.next_run_at)
        self.created_at = ensure_utc(self.created_at)

        if self.last_run_at is not None:
            self.last_run_at = ensure_utc(self.last_run_at)


@dataclass
class ScheduleOccurrence:
    schedule_id: str
    job_id: str
    scheduled_for: datetime
    id: str = field(default_factory=lambda: str(uuid4()))
    status: OccurrenceStatus = OccurrenceStatus.CLAIMED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        self.scheduled_for = ensure_utc(self.scheduled_for)

        if self.started_at is not None:
            self.started_at = ensure_utc(self.started_at)

        if self.finished_at is not None:
            self.finished_at = ensure_utc(self.finished_at)