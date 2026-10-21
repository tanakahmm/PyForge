
import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from pyforge.domain.schedule import Schedule, ScheduleOccurrence
from pyforge.engine.executor import Executor
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.exceptions import ScheduleNotFoundError
from pyforge.engine.manager import JobManager
from pyforge.storage.schedule_repository import ScheduleRepository
import logging


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

logger = logging.getLogger(__name__)
class SchedulerService:
    def __init__(
        self,
        manager: JobManager,
        repository: ScheduleRepository,
        *,
        poll_interval: float = 1.0,
        misfire_grace_seconds: float = 5.0,
        max_concurrency: int = 4,
        executor_factory: Callable[[], Executor] = SyncExecutor,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        if misfire_grace_seconds < 0:
            raise ValueError("misfire grace cannot be negative")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        self.manager = manager
        self.repository = repository
        self.poll_interval = poll_interval
        self.misfire_grace_seconds = misfire_grace_seconds
        self.max_concurrency = max_concurrency
        self.executor_factory = executor_factory
        self.clock = clock

        self._loop_task: asyncio.Task | None = None
        self._tasks: dict[str, asyncio.Task] = {}
        self._busy_schedule_ids: set[str] = set()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._stopping = False
        logger = logging.getLogger(__name__)

    def create_interval_schedule(
        self,
        job_id: str,
        interval_seconds: float,
    ) -> Schedule:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

        # Verify the referenced job exists before storing the schedule.
        self.manager.get_job(job_id)

        now = self.clock()
        schedule = Schedule(
            job_id=job_id,
            interval_seconds=interval_seconds,
            next_run_at=now + timedelta(seconds=interval_seconds),
            created_at=now,
        )
        self.repository.create_schedule(schedule)
        return schedule

    def get_schedule(self, schedule_id: str) -> Schedule:
        return self.repository.get_schedule(schedule_id)

    def list_schedules(self) -> list[Schedule]:
        return self.repository.list_schedules()

    def delete_schedule(self, schedule_id: str) -> None:
        if schedule_id in self._busy_schedule_ids:
            raise ValueError("Cannot delete a schedule while it is running")
        self.repository.delete_schedule(schedule_id)

    def set_enabled(
        self,
        schedule_id: str,
        enabled: bool,
    ) -> Schedule:
        return self.repository.set_enabled(
            schedule_id, enabled, self.clock()
        )

    def list_occurrences(
        self,
        schedule_id: str,
    ) -> list[ScheduleOccurrence]:
        # Confirm the schedule exists even if it has no occurrences.
        self.repository.get_schedule(schedule_id)
        return self.repository.list_occurrences(schedule_id)

    async def run_once(self) -> list[ScheduleOccurrence]:
        """Claim due schedules and dispatch them without blocking the poll loop."""
        due = self.repository.claim_due(
            now=self.clock(),
            grace_seconds=self.misfire_grace_seconds,
            excluded_schedule_ids=set(self._busy_schedule_ids),
        )

        for occurrence in due:
            self._busy_schedule_ids.add(occurrence.schedule_id)
            task = asyncio.create_task(
                self._execute_occurrence(occurrence)
            )
            self._tasks[occurrence.id] = task

        return due

    async def _execute_occurrence(
        self,
        occurrence: ScheduleOccurrence,
    ) -> None:
        try:
            async with self._semaphore:
                self.repository.mark_running(
                    occurrence.id, self.clock()
                )

                # JobManager and its executors are synchronous.
                result = await asyncio.to_thread(
                    self.manager.execute_job,
                    occurrence.job_id,
                    self.executor_factory(),
                )

                success = result.status.value == "success"
                self.repository.finish_occurrence(
                    occurrence.id,
                    status="success" if success else "failed",
                    finished_at=self.clock(),
                    error=None if success else (
                        result.error or result.stderr or
                        f"Job finished with status {result.status.value}"
                    ),
                )

        except asyncio.CancelledError:
            # Do not silently turn cancellation into success.
            raise
        except Exception as exc:
            try:
                self.repository.finish_occurrence(
                    occurrence.id,
                    status="failed",
                    finished_at=self.clock(),
                    error=str(exc),
                )
            except ValueError:
                # The occurrence may already have been finalized.
                pass
        finally:
            self._busy_schedule_ids.discard(
                occurrence.schedule_id
            )
            self._tasks.pop(occurrence.id, None)

    async def wait_for_idle(self) -> None:
        """Wait for currently dispatched executions; useful in tests."""
        while self._tasks:
            tasks = list(self._tasks.values())
            await asyncio.gather(*tasks, return_exceptions=True)

    async def start(self) -> None:
        if self._loop_task is not None:
            raise RuntimeError("Scheduler is already running")

        self.repository.recover_incomplete(self.clock())
        self._stopping = False
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def _run_loop(self) -> None:
        while not self._stopping:
            await self.run_once()
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._stopping = True

        if self._loop_task is not None:
            self._loop_task.cancel()
            try:
                await self._loop_task
                logger.info("Scheduler shutdown requested")
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        # Graceful shutdown: let already-dispatched jobs finish.
        await self.wait_for_idle()
        logger.info("Scheduler stopped")
