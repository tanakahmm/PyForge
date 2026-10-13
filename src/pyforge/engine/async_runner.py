import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar


T = TypeVar("T")
R = TypeVar("R")


class AsyncTaskRunner:
    """Run asynchronous tasks with a concurrency limit."""

    def __init__(self, max_concurrency: int = 10) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        self.max_concurrency = max_concurrency

    async def map(
        self,
        function: Callable[[T], Awaitable[R]],
        items: Iterable[T],
    ) -> list[R]:
        """Run an async function for each item, preserving input order."""

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_one(item: T) -> R:
            async with semaphore:
                return await function(item)

        tasks = [run_one(item) for item in items]

        return list(await asyncio.gather(*tasks))
