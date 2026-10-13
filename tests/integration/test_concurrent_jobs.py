
import sys

import pytest

from pyforge.engine.manager import JobManager
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.storage.sqlite_repository import SQLiteRepository


@pytest.fixture
def manager(tmp_path):
    repository = SQLiteRepository(tmp_path / "concurrent.db")
    return JobManager(repository=repository)


def test_multiple_jobs_execute_concurrently(manager):
    jobs = [
        manager.create_job(
            name=f"job-{i}",
            command=[
                sys.executable,
                "-c",
                f"print('output-{i}')",
            ],
        )
        for i in range(3)
    ]

    results = manager.execute_jobs_concurrently(
        [job.id for job in jobs],
        executor_factory=SyncExecutor,
        max_workers=3,
    )

    assert len(results) == 3
    assert [result.job_id for result in results] == [
        job.id for job in jobs
    ]

    for i, result in enumerate(results):
        assert result.status.value == "success"
        assert result.stdout.strip() == f"output-{i}"

        # Verify the final status was persisted.
        saved_job = manager.get_job(result.job_id)
        assert saved_job.status.value == "success"

        # Verify the result was persisted.
        saved_result = manager.get_result(result.job_id)
        assert saved_result.stdout == result.stdout


def test_empty_job_list_returns_empty_results(manager):
    results = manager.execute_jobs_concurrently(
        [],
        executor_factory=SyncExecutor,
    )

    assert results == []


def test_zero_workers_is_rejected(manager):
    with pytest.raises(ValueError, match="max_workers"):
        manager.execute_jobs_concurrently(
            [],
            executor_factory=SyncExecutor,
            max_workers=0,
        )


def test_duplicate_job_ids_are_rejected(manager):
    job = manager.create_job(
        name="duplicate-test",
        command=[sys.executable, "-c", "print('hello')"],
    )

    with pytest.raises(ValueError, match="Duplicate"):
        manager.execute_jobs_concurrently(
            [job.id, job.id],
            executor_factory=SyncExecutor,
        )
