import pytest
from datetime import datetime
from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult
from pyforge.serialization.json_serializer import JSONSerializer


@pytest.fixture
def serializer():
    return JSONSerializer()


def test_json_job_serialization(serializer):
    original_job = Job(
        name="backup-db",
        command=["pg_dump", "production"],
        timeout=60.0,
        status=JobStatus.PENDING,
        metadata={"environment":"production","owner":"platform-team"}
    )

    json_str = serializer.serialize(original_job)
    assert isinstance(json_str, str)
    assert '"status": "pending"' in json_str

    restored_job = serializer.deserialize(json_str)

    assert restored_job is not original_job
    assert isinstance(restored_job, Job)

    assert restored_job.id == original_job.id
    assert restored_job.name == original_job.name
    assert restored_job.command == original_job.command
    assert restored_job.status == JobStatus.PENDING
    assert restored_job.metadata==original_job.metadata

    assert isinstance(restored_job.status, JobStatus)
    assert isinstance(restored_job.created_at, datetime)


def test_json_job_result_serialization(serializer):
    now = datetime.utcnow()
    original_result = JobResult(
        job_id="test-1234",
        status=JobStatus.SUCCESS,
        stdout="Done",
        stderr="",
        exit_code=0,
        started_at=now,
        finished_at=now,
        error=None,
    )

    json_str = serializer.serialize(original_result)
    restored_result = serializer.deserialize(json_str)

    assert restored_result is not original_result
    assert isinstance(restored_result, JobResult)

    assert restored_result.status == JobStatus.SUCCESS
    assert restored_result.exit_code == 0
    assert restored_result.job_id==original_result.job_id
    assert restored_result.stdout=="Done"
    assert restored_result.started_at==now