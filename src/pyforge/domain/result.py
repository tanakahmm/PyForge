from dataclasses import dataclass
from datetime import datetime

from .job import JobStatus


@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    stdout: str
    stderr: str
    exit_code: int
    started_at: datetime
    finished_at: datetime
    error: str | None = None