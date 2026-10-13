from datetime import datetime

import pytest

from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult
from pyforge.engine.manager import JobManager
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.exceptions import JobNotFoundError, JobResultNotFoundError
from pyforge.storage.sqlite_repository import SQLiteRepository


@pytest.fixture
def repository(tmp_path):
    db_path = tmp_path / "test_pyforge.db"
    return SQLiteRepository(db_path)


def test_job_survives_repository_restart(repository, tmp_path):
    job = Job(
        name="persistent-job",
        command=["echo", "hello"],
        metadata={"owner": "platform-team"},
    )

    repository.save_job(job)

    reopened = SQLiteRepository(tmp_path / "test_pyforge.db")
    restored = reopened.get_job(job.id)

    assert restored is not job
    assert restored.id == job.id
    assert restored.name == job.name
    assert restored.command == job.command
    assert restored.status == JobStatus.PENDING
    assert restored.created_at == job.created_at
    assert restored.metadata == job.metadata


def test_execution_result_is_persisted(repository):
    manager = JobManager(repository=repository)
    job = manager.create_job(
        "hello",
        ["echo", "hello"],
    )

    result = manager.execute_job(job.id, SyncExecutor())

    reopened = SQLiteRepository(repository.db_path)
    restored_job = reopened.get_job(job.id)
    restored_result = reopened.get_result(job.id)

    assert restored_job.status == JobStatus.SUCCESS
    assert restored_result.job_id == job.id
    assert restored_result.status == JobStatus.SUCCESS
    assert restored_result.stdout.strip() == "hello"
    assert restored_result.exit_code == 0


def test_result_round_trip(repository):
    job = Job("result-test", ["echo", "ok"])
    repository.save_job(job)

    now = datetime.utcnow()
    result = JobResult(
        job_id=job.id,
        status=JobStatus.SUCCESS,
        stdout="ok\n",
        stderr="",
        exit_code=0,
        started_at=now,
        finished_at=now,
        error=None,
    )

    repository.save_result(result)
    restored = repository.get_result(job.id)

    assert restored is not result
    assert restored.status == result.status
    assert restored.stdout == result.stdout
    assert restored.started_at == result.started_at


def test_missing_job_raises_error(repository):
    with pytest.raises(JobNotFoundError):
        repository.get_job("does-not-exist")


def test_missing_result_raises_error(repository):
    job = Job("no-result", ["echo", "hello"])
    repository.save_job(job)

    with pytest.raises(JobResultNotFoundError):
        repository.get_result(job.id)


def test_deleting_job_deletes_its_result(repository):
    manager = JobManager(repository=repository)
    job = manager.create_job("to-delete", ["echo", "hello"])
    manager.execute_job(job.id, SyncExecutor())

    manager.remove_job(job.id)

    with pytest.raises(JobNotFoundError):
        repository.get_job(job.id)

    with pytest.raises(JobResultNotFoundError):
        repository.get_result(job.id)


def test_list_jobs(repository):
    first = Job("first", ["echo", "one"])
    second = Job("second", ["echo", "two"])

    repository.save_job(first)
    repository.save_job(second)

    jobs = repository.list_jobs()

    assert len(jobs) == 2
    assert {job.id for job in jobs} == {first.id, second.id}


def test_update_job_status(repository):
    job = Job("update-test", ["echo", "hello"])
    repository.save_job(job)

    job.status = JobStatus.SUCCESS
    repository.save_job(job)

    restored = repository.get_job(job.id)
    assert restored.status == JobStatus.SUCCESS