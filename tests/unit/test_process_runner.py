
import os

import pytest

from pyforge.engine.process_runner import ProcessTaskRunner


# Keep worker functions at module scope so they can be pickled.
def square(number: int) -> int:
    return number * number


def get_process_id(_: int) -> int:
    return os.getpid()


def test_process_runner_maps_values():
    runner = ProcessTaskRunner(max_workers=2)

    results = runner.map(square, [1, 2, 3, 4])

    assert results == [1, 4, 9, 16]


def test_process_runner_uses_worker_processes():
    runner = ProcessTaskRunner(max_workers=2)

    process_ids = runner.map(get_process_id, [1, 2])

    assert len(process_ids) == 2
    assert all(pid != os.getpid() for pid in process_ids)


def test_process_runner_handles_empty_input():
    runner = ProcessTaskRunner(max_workers=2)

    assert runner.map(square, []) == []


def test_invalid_worker_count_is_rejected():
    with pytest.raises(ValueError, match="max_workers"):
        ProcessTaskRunner(max_workers=0)
