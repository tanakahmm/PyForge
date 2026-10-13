import json
from datetime import datetime
from typing import Any
from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult


class JSONSerializer:
    """Serializes and deserializes PyForge domain objects to and from JSON strings."""

    def serialize(self, obj: Any) -> str:
        """Convert a Job or JobResult into a JSON string."""
        if isinstance(obj, Job):
            data = {
                "__type__": "Job",
                "id": obj.id,
                "name": obj.name,
                "command": obj.command,
                "timeout": obj.timeout,
                "status": obj.status.value, 
                "created_at": obj.created_at.isoformat(),
                "metadata":obj.metadata,
            }
            return json.dumps(data, indent=2)

        elif isinstance(obj, JobResult):
            data = {
                "__type__": "JobResult",
                "job_id": obj.job_id,
                "status": obj.status.value,
                "stdout": obj.stdout,
                "stderr": obj.stderr,
                "exit_code": obj.exit_code,
                "started_at": obj.started_at.isoformat(),
                "finished_at": obj.finished_at.isoformat(),
                "error": obj.error,
            }
            return json.dumps(data, indent=2)

        raise TypeError(f"Type {type(obj)} is not supported by JSONSerializer")

    def deserialize(self, data_str: str) -> Any:
        """Reconstruct a Job or JobResult from a JSON string."""
        data = json.loads(data_str)
        type_name = data.get("__type__")

        if type_name == "Job":
            return Job(
                id=data["id"],
                name=data["name"],
                command=data["command"],
                timeout=data["timeout"],
                status=JobStatus(data["status"]), 
                created_at=datetime.fromisoformat(data["created_at"]),
                metadata=data.get("metadata",{})
            )

        elif type_name == "JobResult":
            return JobResult(
                job_id=data["job_id"],
                status=JobStatus(data["status"]),
                stdout=data["stdout"],
                stderr=data["stderr"],
                exit_code=data["exit_code"],
                started_at=datetime.fromisoformat(data["started_at"]),
                finished_at=datetime.fromisoformat(data["finished_at"]),
                error=data.get("error"),
            )

        raise ValueError(f"Unknown object type: {type_name}")