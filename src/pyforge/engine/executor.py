from abc import ABC, abstractmethod

from pyforge.domain.job import Job
from pyforge.domain.result import JobResult


class Executor(ABC):

    @abstractmethod
    def execute(self, job: Job) -> JobResult:
        pass