from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from typing import TypeVar


T = TypeVar("T")
R = TypeVar("R")


class ProcessTaskRunner:
    """Run independent, picklable Python tasks in worker processes."""

    def __init__(self, max_workers: int | None = None) -> None:
        if max_workers is not None and max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        self.max_workers = max_workers

    def map(
        self,
        function: Callable[[T], R],
        items: Iterable[T],
    ) -> list[R]:
        """Execute function(item) across multiple worker processes."""

        with ProcessPoolExecutor(
            max_workers=self.max_workers
        ) as pool:
            return list(pool.map(function, items))
