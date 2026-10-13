import pytest
from pyforge.domain.job import Job
from pyforge.engine.manager import JobManager
from _pytest import pytester_assertions
from pyforge.exceptions import JobNotFoundError
@pytest.fixture
def manager():
    return JobManager()

def test_create_job(manager):
    job=manager.create_job("backup",["echo","hello"])
    assert isinstance(job,Job)
    assert job.name=="backup"
    assert job.command==["echo","hello"]

def test_get_job(manager):
    job=manager.create_job("backup",["echo","hello"])
    result=manager.get_job(job.id)
    assert result is job

def test_get_missing_job(manager):

    with pytest.raises(JobNotFoundError):
        manager.get_job("does-not-exist")


def test_list_jobs(manager):

    manager.create_job("one", ["echo", "one"])
    manager.create_job("two", ["echo", "two"])

    jobs = manager.list_jobs()

    assert len(jobs) == 2


def test_remove_job(manager):

    job = manager.create_job(
        "backup",
        ["echo", "hello"],
    )

    manager.remove_job(job.id)

    with pytest.raises(JobNotFoundError):
        manager.get_job(job.id)

