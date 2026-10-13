from pyforge.storage.repository import JobRepository
from pyforge.domain.job import Job
from pyforge.domain.result import JobResult
from pyforge.exceptions import JobNotFoundError,JobResultNotFoundError
class MemoryRepository(JobRepository):
    """store jobs and results in memory"""
    def __init__(self)->None:
        self._jobs:dict[str,Job]={}
        self._results:dict[str,JobResult]={}
    
    def save_job(self,job:Job)->None:
        self._jobs[job.id]=job
    
    def get_job(self, job_id: str) -> Job:
        try:
            return self._jobs[job_id]
        except KeyError:
            raise JobNotFoundError(
                f"Job '{job_id}' was not found"
            ) from None

    def list_jobs(self) -> list[Job]:
        return list(self._jobs.values())

    def delete_job(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise JobNotFoundError(
                f"Job '{job_id}' was not found"
            )

        del self._jobs[job_id]
        self._results.pop(job_id, None)

    def save_result(self, result: JobResult) -> None:
        if result.job_id not in self._jobs:
            raise JobNotFoundError(
                f"Job '{result.job_id}' was not found"
            )

        self._results[result.job_id] = result

    def get_result(self, job_id: str) -> JobResult:
        try:
            return self._results[job_id]
        except KeyError:
            raise JobResultNotFoundError(
                f"Result for job '{job_id}' was not found"
            ) from None

    def list_results(self) -> list[JobResult]:
        return list(self._results.values())