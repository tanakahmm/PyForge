
from pyforge.domain.job import Job
from pyforge.domain.result import JobResult
from pyforge.engine.executor import Executor
from pyforge.storage.memory_repository import MemoryRepository
from pyforge.storage.repository import JobRepository
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable

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
        self._repository.save_job(job)
        return job

    def get_job(self, job_id: str) -> Job:
        return self._repository.get_job(job_id)

    def list_jobs(self) -> list[Job]:
        return self._repository.list_jobs()

    def remove_job(self, job_id: str) -> None:
        self._repository.delete_job(job_id)

    def execute_job(
        self, job_id: str, executor: Executor
    ) -> JobResult:
        job = self._repository.get_job(job_id)
        result = executor.execute(job)

        # Persist both the final job status and its result.
        self._repository.save_job(job)
        self._repository.save_result(result)

        return result

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
