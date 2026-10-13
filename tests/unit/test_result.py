from pyforge.domain.job import JobStatus
from pyforge.domain.result import JobResult
from datetime import datetime
def job_result_creating():
    now=datetime.utc.now()
    result=JobResult(job_id="test-123",status=JobStatus.SUCCESS,stdout="hello",stderr="",exit_code=0,started_at=now,finished_at=now)
    assert result.job_id=="test-123"
    assert result.status==JobStatus.SUCCESS
    assert result.stdout=="hello"
    assert result.stderr==""
    assert result.exit_code==0
    assert result.error is None
