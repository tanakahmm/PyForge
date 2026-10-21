from pyforge.domain.job import Job
from pyforge.domain.result import JobResult
from pyforge.engine.executor import Executor
from pyforge.storage.memory_repository import MemoryRepository
from pyforge.storage.repository import JobRepository
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
import logging
from time import perf_counter
from pyforge.observability.metrics import metrics

logger = logging.getLogger(__name__)
class JobManager:
    def __init__(
        self,
        repository: JobRepository | None = None,
    ) -> None:
        self._repository = (
            repository if repository is not None
            else MemoryRepository()
        )

    def create_job(
        self,
        name: str,
        command: list[str],
        timeout: float | None = 30.0,
        metadata: dict[str, str] | None = None,
    ) -> Job:
        job = Job(
            name=name,
            command=command,
            timeout=timeout,
            metadata={} if metadata is None else metadata,
        )
        logger.info(
                "Job created job_id=%s name=%s",
                job.id,
                job.name,
            )
        self._repository.save_job(job)
        return job

    def get_job(self, job_id: str) -> Job:
        return self._repository.get_job(job_id)

    def list_jobs(self) -> list[Job]:
        return self._repository.list_jobs()

    def remove_job(self, job_id: str) -> None:
        self._repository.delete_job(job_id)

    def execute_job(self, job_id: str, executor: Executor) -> JobResult:
        job = self._repository.get_job(job_id)
        started=perf_counter()

        logger.info("Job execution started job_id=%s", job_id)

        try:
            result = executor.execute(job)

            self._repository.save_job(job)
            self._repository.save_result(result)

            duration=perf_counter()-started
            metrics.record_job(result.status.value, duration)
            if result.status.value == "success":
                logger.info(
                    "Job execution completed job_id=%s status=%s duration=%.4f",
                    job_id,
                    result.status.value,
                    duration,
                )
            else:
                logger.warning(
                    "Job execution finished unsuccessfully "
                    "job_id=%s status=%s duration=%.4f",
                    job_id,
                    result.status.value,
                    duration,
                )

            return result
            metrics.record_job(result.status.value, perf_counter()- started,)

        except Exception:
            duration=perf_counter()-started
            logger.exception(
                "Job execution raised an exception job_id=%s duration=%.4f",
                job_id,
                duration,
            )
            metrics.record_job("exception", perf_counter()- started,)
            raise

    def execute_jobs_concurrently(
        self,
        job_ids: list[str],
        executor_factory: Callable[[], Executor],
        max_workers: int = 4,
    ) -> list[JobResult]:
        """Execute multiple jobs concurrently using worker threads."""

        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        if len(set(job_ids)) != len(job_ids):
            raise ValueError("Duplicate job IDs are not allowed")

        if not job_ids:
            return []

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(
                    self._execute_with_factory,
                    job_id,
                    executor_factory,
                )
                for job_id in job_ids
            ]

            # Collect results in the same order as job_ids.
            return [future.result() for future in futures]

    def _execute_with_factory(
        self,
        job_id: str,
        executor_factory: Callable[[], Executor],
    ) -> JobResult:
        """Create an executor for one job and execute it."""

        executor = executor_factory()
        return self.execute_job(job_id, executor)


    def get_result(self, job_id: str) -> JobResult:
        return self._repository.get_result(job_id)

    def list_results(self) -> list[JobResult]:
        return self._repository.list_results()
