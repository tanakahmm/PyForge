
import asyncio

import pytest

from pyforge.engine.async_runner import AsyncTaskRunner


async def double_after_delay(number: int) -> int:
    await asyncio.sleep(0.01)
    return number * 2


def test_async_runner_maps_values_in_input_order():
    runner = AsyncTaskRunner(max_concurrency=3)

    results = asyncio.run(
        runner.map(double_after_delay, [3, 1, 2])
    )

    assert results == [6, 2, 4]


def test_async_runner_handles_empty_input():
    runner = AsyncTaskRunner()

    results = asyncio.run(runner.map(double_after_delay, []))

    assert results == []


def test_invalid_concurrency_is_rejected():
    with pytest.raises(ValueError, match="max_concurrency"):
        AsyncTaskRunner(max_concurrency=0)


def test_async_runner_respects_concurrency_limit():
    async def scenario():
        runner = AsyncTaskRunner(max_concurrency=2)
        active = 0
        peak_active = 0

        async def tracked_task(value: int) -> int:
            nonlocal active, peak_active

            active += 1
            peak_active = max(peak_active, active)

            try:
                await asyncio.sleep(0.02)
                return value
            finally:
                active -= 1

        results = await runner.map(tracked_task, range(6))

        assert results == list(range(6))
        assert peak_active == 2

    asyncio.run(scenario())


def test_async_runner_propagates_task_exceptions():
    async def failing_task(_: int) -> int:
        raise ValueError("task failed")

    runner = AsyncTaskRunner()

    with pytest.raises(ValueError, match="task failed"):
        asyncio.run(runner.map(failing_task, [1]))
