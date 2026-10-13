import pytest
from pyforge.domain.job import Job, JobStatus
from pyforge.engine.sync_executor import SyncExecutor


@pytest.fixture
def executor():
    return SyncExecutor()


def test_execute_success(executor):
    job = Job(name="test-success", command=["echo", "hello world"])
    result = executor.execute(job)

    assert result.status == JobStatus.SUCCESS
    assert job.status == JobStatus.SUCCESS
    assert "hello world" in result.stdout
    assert result.exit_code == 0
    assert result.error is None


def test_execute_failure(executor):
    job = Job(name="test-failure", command=["python3", "-c", "import sys; sys.exit(2)"])
    result = executor.execute(job)

    assert result.status == JobStatus.FAILED
    assert job.status == JobStatus.FAILED
    assert result.exit_code == 2


def test_execute_timeout(executor):
    job = Job(name="test-timeout", command=["sleep", "2"], timeout=0.1)
    result = executor.execute(job)

    assert result.status == JobStatus.TIMEOUT
    assert job.status == JobStatus.TIMEOUT
    assert result.exit_code is None
    assert "timed out" in result.error.lower()


def test_execute_missing_command(executor):
    job = Job(name="test-missing", command=["non_existent_command_12345"])
    result = executor.execute(job)

    assert result.status == JobStatus.FAILED
    assert job.status == JobStatus.FAILED
    assert result.exit_code is None
    assert "executable not found" in result.error.lower()