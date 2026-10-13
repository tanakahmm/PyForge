
from abc import ABC, abstractmethod

from pyforge.engine.executor import Executor


class ExecutorPlugin(ABC):
    """Base contract for plugins that provide executors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name used to select this plugin."""
        raise NotImplementedError

    @abstractmethod
    def create_executor(self) -> Executor:
        """Create an executor supplied by this plugin."""
        raise NotImplementedError
