
from abc import ABC, abstractmethod
from datetime import datetime

from pyforge.domain.schedule import Schedule, ScheduleOccurrence


class ScheduleRepository(ABC):
    @abstractmethod
    def create_schedule(self, schedule: Schedule) -> None:
        pass

    @abstractmethod
    def get_schedule(self, schedule_id: str) -> Schedule:
        pass

    @abstractmethod
    def list_schedules(self) -> list[Schedule]:
        pass

    @abstractmethod
    def delete_schedule(self, schedule_id: str) -> None:
        pass

    @abstractmethod
    def set_enabled(
        self,
        schedule_id: str,
        enabled: bool,
        now: datetime,
    ) -> Schedule:
        pass

    @abstractmethod
    def claim_due(
        self,
        now: datetime,
        grace_seconds: float,
        excluded_schedule_ids: set[str],
    ) -> list[ScheduleOccurrence]:
        pass

    @abstractmethod
    def mark_running(
        self,
        occurrence_id: str,
        started_at: datetime,
    ) -> None:
        pass

    @abstractmethod
    def finish_occurrence(
        self,
        occurrence_id: str,
        status: str,
        finished_at: datetime,
        error: str | None = None,
    ) -> None:
        pass

    @abstractmethod
    def list_occurrences(
        self,
        schedule_id: str,
    ) -> list[ScheduleOccurrence]:
        pass

    @abstractmethod
    def recover_incomplete(
        self,
        now: datetime,
    ) -> int:
        pass
