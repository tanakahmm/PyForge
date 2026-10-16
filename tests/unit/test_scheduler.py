import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from pyforge.domain.schedule import OccurrenceStatus
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.engine.manager import JobManager
from pyforge.scheduler import SchedulerService
from pyforge.storage.memory_repository import MemoryRepository
from pyforge.storage.sqlite_schedule_repository import (
    SQLiteScheduleRepository,
)


def test_schedule_survives_repository_reopen(tmp_path):
    db_path = tmp_path / "schedules.db"
    manager = JobManager(repository=MemoryRepository())
    job = manager.create_job("hello", ["python3", "-c", "pass"])

    schedule_repo = SQLiteScheduleRepository(db_path)
    schedule = SchedulerService(
        manager,
        schedule_repo,
    ).create_interval_schedule(job.id, 60)

    reopened_repo = SQLiteScheduleRepository(db_path)

    restored = reopened_repo.get_schedule(schedule.id)
    assert restored.job_id == job.id
    assert restored.interval_seconds == 60
    assert restored.next_run_at == schedule.next_run_at


def test_schedule_rejects_non_positive_interval():
    manager = JobManager(repository=MemoryRepository())
    job = manager.create_job("hello", ["python3", "-c", "pass"])

    scheduler = SchedulerService(
        manager,
        SQLiteScheduleRepository(":memory:"),
    )

    with pytest.raises(ValueError):
        scheduler.create_interval_schedule(job.id, 0)


def test_due_occurrence_executes_job():
    async def scenario():
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        clock_value = [now]

        manager = JobManager(repository=MemoryRepository())
        job = manager.create_job(
            "scheduled-hello",
            ["python3", "-c", "print('scheduled')"],
        )
        repository = SQLiteScheduleRepository(":memory:")
        scheduler = SchedulerService(
            manager,
            repository,
            executor_factory=SyncExecutor,
            clock=lambda: clock_value[0],
        )

        schedule = scheduler.create_interval_schedule(
            job.id, interval_seconds=10
        )

        clock_value[0] = now + timedelta(seconds=10)
        claimed = await scheduler.run_once()

        assert len(claimed) == 1
        assert claimed[0].schedule_id == schedule.id

        await scheduler.wait_for_idle()

        occurrences = scheduler.list_occurrences(schedule.id)
        assert len(occurrences) == 1
        assert occurrences[0].status == OccurrenceStatus.SUCCESS

        result = manager.get_result(job.id)
        assert result.status.value == "success"
        assert "scheduled" in result.stdout

    asyncio.run(scenario())


def test_old_missed_occurrences_are_skipped():
    async def scenario():
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        clock_value = [now]

        manager = JobManager(repository=MemoryRepository())
        job = manager.create_job("missed", ["python3", "-c", "pass"])
        repository = SQLiteScheduleRepository(":memory:")
        scheduler = SchedulerService(
            manager,
            repository,
            clock=lambda: clock_value[0],
            misfire_grace_seconds=2,
        )

        schedule = scheduler.create_interval_schedule(
            job.id, interval_seconds=5
        )

        # First occurrence was due at +5 seconds.
        clock_value[0] = now + timedelta(seconds=16)
        claimed = await scheduler.run_once()

        assert claimed == []

        restored = scheduler.get_schedule(schedule.id)
        assert restored.missed_runs == 3
        assert restored.next_run_at == now + timedelta(seconds=20)
        assert scheduler.list_occurrences(schedule.id) == []

    asyncio.run(scenario())


def test_restart_marks_incomplete_occurrences_interrupted():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manager = JobManager(repository=MemoryRepository())
    job = manager.create_job("restart", ["python3", "-c", "pass"])
    repository = SQLiteScheduleRepository(":memory:")

    scheduler = SchedulerService(
        manager,
        repository,
        clock=lambda: now,
    )
    schedule = scheduler.create_interval_schedule(
        job.id, interval_seconds=5
    )

    claimed = repository.claim_due(
        now=now + timedelta(seconds=5),
        grace_seconds=1,
        excluded_schedule_ids=set(),
    )
    assert len(claimed) == 1

    recovered = repository.recover_incomplete(
        now + timedelta(seconds=6)
    )

    assert recovered == 1
    occurrences = repository.list_occurrences(schedule.id)
    assert occurrences[0].status == OccurrenceStatus.INTERRUPTED


def test_disabled_schedule_is_not_claimed():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    manager = JobManager(repository=MemoryRepository())
    job = manager.create_job("disabled", ["python3", "-c", "pass"])
    repository = SQLiteScheduleRepository(":memory:")

    scheduler = SchedulerService(
        manager,
        repository,
        clock=lambda: now,
    )
    schedule = scheduler.create_interval_schedule(
        job.id, interval_seconds=5
    )
    scheduler.set_enabled(schedule.id, False)

    claimed = repository.claim_due(
        now=now + timedelta(seconds=10),
        grace_seconds=5,
        excluded_schedule_ids=set(),
    )

    assert claimed == []


def test_repository_rejects_missing_schedule():
    from pyforge.exceptions import ScheduleNotFoundError

    repository = SQLiteScheduleRepository(":memory:")

    with pytest.raises(ScheduleNotFoundError):
        repository.get_schedule("does-not-exist")
