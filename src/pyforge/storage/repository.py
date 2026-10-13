from abc import abstractmethod
from pyforge.domain.job import Job
from pyforge.domain.result import JobResult
from abc import ABC
class JobRepository(ABC):
    """Contract for persisting jobs and their results"""
    @abstractmethod
    def save_job(self,job: Job)->None:
        """Insert or update a job"""
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: str) -> Job:
        """Retrieve a job by ID."""
        raise NotImplementedError
    
    @abstractmethod
    def list_jobs(self) -> list[Job]:
        """Return all stored jobs."""
        raise NotImplementedError

    @abstractmethod
    def delete_job(self, job_id: str) -> None:
        """Delete a job and its associated result."""
        raise NotImplementedError

    @abstractmethod
    def save_result(self, result: JobResult) -> None:
        """Insert or update an execution result."""
        raise NotImplementedError

    @abstractmethod
    def get_result(self, job_id: str) -> JobResult:
        """Retrieve the result associated with a job."""
        raise NotImplementedError

    @abstractmethod
    def list_results(self) -> list[JobResult]:
        """Return all stored results."""
        raise NotImplementedError