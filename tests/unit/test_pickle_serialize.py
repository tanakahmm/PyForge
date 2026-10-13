import pytest
from datetime import datetime
from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult
from pyforge.serialization.pickle_serializer import PickleSerializer


@pytest.fixture
def serializer():
    return PickleSerializer()


def test_pickle_job_serialization(serializer):
    original_job = Job(
        name="backup-db",
        command=["pg_dump", "production"],
        timeout=60.0,
        status=JobStatus.PENDING,
        metadata={"environment":"production","owner":"platform-team"}
    )

    serialized_bytes = serializer.serialize(original_job)

    assert isinstance(serialized_bytes, bytes)

    restored_job = serializer.deserialize(serialized_bytes)

    assert restored_job is not original_job

    assert isinstance(restored_job, Job)
    assert restored_job.id == original_job.id
    assert restored_job.name == original_job.name
    assert restored_job.command == original_job.command
    assert restored_job.timeout == original_job.timeout
    assert restored_job.status == JobStatus.PENDING
    assert isinstance(restored_job.status, JobStatus)
    assert restored_job.created_at == original_job.created_at
    assert restored_job.metadata == original_job.metadata


def test_pickle_job_result_serialization(serializer):
    now = datetime.utcnow()
    original_result = JobResult(
        job_id="test-uuid-1234",
        status=JobStatus.SUCCESS,
        stdout="Dump completed.",
        stderr="",
        exit_code=0,
        started_at=now,
        finished_at=now,
        error=None,
    )

    serialized_bytes = serializer.serialize(original_result)
    restored_result = serializer.deserialize(serialized_bytes)

    assert restored_result is not original_result
    assert isinstance(restored_result, JobResult)
    assert restored_result.job_id == original_result.job_id
    assert restored_result.status == JobStatus.SUCCESS
    assert restored_result.stdout == "Dump completed."
    assert restored_result.exit_code == 0
    assert restored_result.started_at == now