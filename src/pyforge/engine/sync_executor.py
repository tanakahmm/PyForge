import subprocess
from datetime import datetime
from pyforge.domain.job import Job, JobStatus
from pyforge.domain.result import JobResult
from pyforge.engine.executor import Executor


class SyncExecutor(Executor):
    def execute(self, job: Job) -> JobResult:
        started_at = datetime.utcnow()
        job.status = JobStatus.RUNNING

        try:
            process = subprocess.run(
                job.command,
                capture_output=True,
                text=True,
                timeout=job.timeout,
            )
            finished_at = datetime.utcnow()

            if process.returncode == 0:
                job.status = JobStatus.SUCCESS
            else:
                job.status = JobStatus.FAILED

            return JobResult(
                job_id=job.id,
                status=job.status,
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode,
                started_at=started_at,
                finished_at=finished_at,
            )

        except subprocess.TimeoutExpired as e:
            finished_at = datetime.utcnow()
            job.status = JobStatus.TIMEOUT
            return JobResult(
                job_id=job.id,
                status=job.status,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""),
                exit_code=None,
                started_at=started_at,
                finished_at=finished_at,
                error=f"Job timed out after {job.timeout} seconds.",
            )

        except FileNotFoundError as e:
            finished_at = datetime.utcnow()
            job.status = JobStatus.FAILED
            return JobResult(
                job_id=job.id,
                status=job.status,
                stdout="",
                stderr="",
                exit_code=None,
                started_at=started_at,
                finished_at=finished_at,
                error=f"Executable not found: {e}",
            )