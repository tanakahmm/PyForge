from pyforge.domain.job import Job,JobStatus

def test_job_defaults():
    job=Job(name="test",command=["echo","hello"])
    assert job.name=="test"
    assert job.command==["echo","hello"]
    assert job.status==JobStatus.PENDING
    assert job.timeout==30.0
    assert job.metadata=={}
    assert job.id
    assert job.created_at

# def test_job_metadata_is_independent():
