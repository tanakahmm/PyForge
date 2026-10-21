from datetime import datetime
from typing import Any
import os
import secrets
from fastapi import FastAPI, HTTPException, Response, status ,Depends ,Header ,Request
from pydantic import BaseModel, Field

from pyforge.domain.job import Job
from pyforge.exceptions import (
    JobNotFoundError,
    JobResultNotFoundError,
    PyForgeError,
)
from pyforge.engine.manager import JobManager
from pyforge.plugins import create_default_registry
from pyforge.storage.sqlite_repository import SQLiteRepository
from dotenv import load_dotenv
from dataclasses import dataclass
from pyforge.domain.schedule import (
    Schedule,
    ScheduleOccurrence,
    utc_now,
)
from pyforge.storage.schedule_repository import ScheduleRepository
from pyforge.exceptions import ScheduleNotFoundError, ScheduleError
from pyforge.scheduler.service import SchedulerService 
from pyforge.storage.sqlite_schedule_repository import SQLiteScheduleRepository
from contextlib import asynccontextmanager
from pyforge.observability.logging_config import configure_logging
import logging
from time import perf_counter
from uuid import uuid4
from pyforge.observability.context import request_id_var
from pyforge.observability.metrics import metrics
from pyforge.observability.logging_config import configure_logging



class CreateJobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    command: list[str] = Field(min_length=1)
    timeout: float | None = Field(default=30.0, gt=0)
    metadata: dict[str, str] = Field(default_factory=dict)

class CreateScheduleRequest(BaseModel):
    job_id: str = Field(min_length=1)
    interval_seconds: float = Field(
        gt=0,
        le=31_536_000,
    )

def serialize_job(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "name": job.name,
        "command": job.command,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "timeout": job.timeout,
        "metadata": job.metadata,
    }


def serialize_result(result) -> dict[str, Any]:
    return {
        "job_id": result.job_id,
        "status": result.status.value,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "error": result.error,
    }

def serialize_schedule(schedule: Schedule) -> dict:
    return {
        "id": schedule.id,
        "job_id": schedule.job_id,
        "interval_seconds": schedule.interval_seconds,
        "next_run_at": schedule.next_run_at.isoformat(),
        "enabled": schedule.enabled,
        "created_at": schedule.created_at.isoformat(),
        "last_run_at": (
            schedule.last_run_at.isoformat()
            if schedule.last_run_at else None
        ),
        "missed_runs": schedule.missed_runs,
    }


def serialize_occurrence(
    occurrence: ScheduleOccurrence,
) -> dict:
    return {
        "id": occurrence.id,
        "schedule_id": occurrence.schedule_id,
        "job_id": occurrence.job_id,
        "scheduled_for": occurrence.scheduled_for.isoformat(),
        "status": occurrence.status.value,
        "started_at": (
            occurrence.started_at.isoformat()
            if occurrence.started_at else None
        ),
        "finished_at": (
            occurrence.finished_at.isoformat()
            if occurrence.finished_at else None
        ),
        "error": occurrence.error,
    }

load_dotenv()
@dataclass(frozen=True)
class Principal:
    name: str
    permissions: frozenset[str]
def create_app(
    manager: JobManager | None = None,
    api_key: str | None = None,
    read_only_api_key: str | None = None,
    readonly_api_key: str | None = None,
    schedule_repository: ScheduleRepository | None = None,
) -> FastAPI:
    if read_only_api_key is not None and readonly_api_key is not None:
        raise ValueError("Specify only one read-only API key argument")

    app = FastAPI(
        title="PyForge API",
        description="HTTP API for managing and executing jobs.",
        version="0.5.0",
    )
    configure_logging()
    job_manager = (
        manager if manager is not None
        else JobManager(SQLiteRepository("pyforge.db"))
    )
    schedule_repo = (
        schedule_repository
        if schedule_repository is not None
        else SQLiteScheduleRepository("pyforge.db")
    )

    scheduler = SchedulerService(
        manager=job_manager,
        repository=schedule_repo,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()

    app = FastAPI(lifespan=lifespan)
    logger = logging.getLogger(__name__)

    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = uuid4().hex
        token = request_id_var.set(request_id)
        started = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception:
            logger.exception(
                "HTTP request raised an exception method=%s path=%s",
                request.method,
                request.url.path,
            )
            raise

        finally:
            duration = perf_counter() - started

            metrics.record_request(
                request.method,
                status_code,
                duration,
            )

            logger.info(
                "HTTP request completed method=%s path=%s "
                "status=%s duration_seconds=%.4f",
                request.method,
                request.url.path,
                status_code,
                duration,
            )

            request_id_var.reset(token)

    app.state.scheduler = scheduler
    app.state.manager = job_manager

    configured_api_key = (
        api_key if api_key is not None
        else os.getenv("PYFORGE_API_KEY")
    )
    configured_readonly_api_key = (
        read_only_api_key
        if read_only_api_key is not None
        else readonly_api_key
        if readonly_api_key is not None
        else os.getenv("PYFORGE_READONLY_API_KEY")
    )

    def get_current_principal(x_api_key: str | None = Header(
    default=None,
    alias="X-API-Key",),) -> Principal:
        if not credential_principals:
            raise HTTPException(
            status_code=503,
            detail="No API credentials are configured",
        )

        if x_api_key is None:
            raise HTTPException(
            status_code=401,
            detail="Missing API key",
        )

        for configured_key, principal in credential_principals:
            if secrets.compare_digest(
            x_api_key, configured_key):
                return principal

        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )


    def require_permission(permission: str):
        def check_permission(
        principal: Principal = Depends(
        get_current_principal),) -> None:
            if permission not in principal.permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions",
                )

        return check_permission

    all_permissions = frozenset({"jobs:read","jobs:create","jobs:execute","jobs:delete","schedules:read","schedules:create","schedules:manage",})
    reader_permissions = frozenset({"jobs:read","schedules:read",})
    credential_principals = []
    if configured_api_key:
        credential_principals.append((configured_api_key,Principal(name="admin",permissions=all_permissions,),))

    if configured_readonly_api_key:
        credential_principals.append((configured_readonly_api_key,Principal(name="reader",permissions=reader_permissions,),))

    plugins = create_default_registry()

    @app.get("/health")
    def health():
        return {"status": "healthy", "service": "pyforge"}

    @app.post(
        "/jobs",
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_permission("jobs:create"))],
    )
    def create_job(request: CreateJobRequest):
        if any(not part for part in request.command):
            raise HTTPException(
                status_code=422,
                detail="Command arguments must not be empty strings",
            )

        try:
            job = job_manager.create_job(
                name=request.name,
                command=request.command,
                timeout=request.timeout,
                metadata=request.metadata,
            )
            return serialize_job(job)
        except PyForgeError as exc:
            raise HTTPException(
                status_code=400, detail=str(exc)
            ) from exc

    @app.get(
        "/jobs",
        dependencies=[Depends(require_permission("jobs:read"))],
    )
    def list_jobs():
        return [
            serialize_job(job)
            for job in job_manager.list_jobs()
        ]

    @app.get(
        "/jobs/{job_id}",
        dependencies=[Depends(require_permission("jobs:read"))],
    )
    def get_job(job_id: str):
        try:
            return serialize_job(job_manager.get_job(job_id))
        except JobNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.post(
        "/jobs/{job_id}/run",
        dependencies=[Depends(require_permission("jobs:execute"))],
    )
    def run_job(job_id: str, executor: str = "sync"):
        try:
            selected_executor = plugins.create_executor(executor)
            result = job_manager.execute_job(
                job_id, selected_executor
            )
            return serialize_result(result)
        except (JobNotFoundError, JobResultNotFoundError) as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc
        except PyForgeError as exc:
            raise HTTPException(
                status_code=400, detail=str(exc)
            ) from exc

    @app.get(
        "/jobs/{job_id}/result",
        dependencies=[Depends(require_permission("jobs:read"))],
    )
    def get_job_result(job_id: str):
        try:
            return serialize_result(
                job_manager.get_result(job_id)
            )
        except (
            JobNotFoundError,
            JobResultNotFoundError,
        ) as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.delete(
        "/jobs/{job_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_permission("jobs:delete"))],
    )
    def delete_job(job_id: str):
        try:
            job_manager.remove_job(job_id)
        except JobNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

        return Response(status_code=status.HTTP_204_NO_CONTENT)


    @app.post(
        "/schedules",
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            Depends(require_permission("schedules:create"))
        ],
    )
    def create_schedule(request: CreateScheduleRequest):
        try:
            schedule = scheduler.create_interval_schedule(
                job_id=request.job_id,
                interval_seconds=request.interval_seconds,
            )
            return serialize_schedule(schedule)
        except JobNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=str(exc)
            ) from exc

    @app.get(
        "/schedules",
        dependencies=[
            Depends(require_permission("schedules:read"))
        ],
    )
    def list_schedules():
        return [
            serialize_schedule(item)
            for item in scheduler.list_schedules()
        ]

    @app.get(
        "/schedules/{schedule_id}",
        dependencies=[
            Depends(require_permission("schedules:read"))
        ],
    )
    def get_schedule(schedule_id: str):
        try:
            return serialize_schedule(
                scheduler.get_schedule(schedule_id)
            )
        except ScheduleNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.get(
        "/schedules/{schedule_id}/occurrences",
        dependencies=[
            Depends(require_permission("schedules:read"))
        ],
    )
    def list_occurrences(schedule_id: str):
        try:
            return [
                serialize_occurrence(item)
                for item in scheduler.list_occurrences(
                    schedule_id
                )
            ]
        except ScheduleNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.post(
        "/schedules/{schedule_id}/enable",
        dependencies=[
            Depends(require_permission("schedules:manage"))
        ],
    )
    def enable_schedule(schedule_id: str):
        try:
            return serialize_schedule(
                scheduler.set_enabled(schedule_id, True)
            )
        except ScheduleNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.post(
        "/schedules/{schedule_id}/disable",
        dependencies=[
            Depends(require_permission("schedules:manage"))
        ],
    )
    def disable_schedule(schedule_id: str):
        try:
            return serialize_schedule(
                scheduler.set_enabled(schedule_id, False)
            )
        except ScheduleNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc

    @app.delete(
        "/schedules/{schedule_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[
            Depends(require_permission("schedules:manage"))
        ],
    )
    def delete_schedule(schedule_id: str):
        try:
            scheduler.delete_schedule(schedule_id)
        except ScheduleNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=409, detail=str(exc)
            ) from exc

        return Response(status_code=status.HTTP_204_NO_CONTENT)


    @app.get(
    "/metrics",dependencies=[Depends(require_permission("jobs:read"))],)
    async def get_metrics():
        return Response(
            content=metrics.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
    )

    @app.get("/ready")
    async def readiness_check():
        try:
            job_manager.list_jobs()
            scheduler.list_schedules()
            return {"status": "ready"}

        except Exception:
            logger.exception("Readiness check failed")

            raise HTTPException(
                status_code=503,
                detail="Application dependencies are unavailable",
            )

    return app


app = create_app()
