from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT ="timeout"


@dataclass
class Job:
    name: str
    command: list[str]
    timeout: float | None =30.0

    id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata:dict[str,str]=field(default_factory=dict)