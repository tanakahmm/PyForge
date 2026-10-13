
from pyforge.engine.executor import Executor
from pyforge.engine.sync_executor import SyncExecutor
from pyforge.plugins.base import ExecutorPlugin


class SyncExecutorPlugin(ExecutorPlugin):
    @property
    def name(self) -> str:
        return "sync"

    def create_executor(self) -> Executor:
        return SyncExecutor()
