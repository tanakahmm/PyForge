from datetime import datetime
from typing import Any
import os
import secrets
from fastapi import FastAPI, HTTPException, Response, status ,Depends ,Header
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

class CreateJobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    command: list[str] = Field(min_length=1)
    timeout: float | None = Field(default=30.0, gt=0)
    metadata: dict[str, str] = Field(default_factory=dict)


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
) -> FastAPI:
    if read_only_api_key is not None and readonly_api_key is not None:
        raise ValueError("Specify only one read-only API key argument")

    app = FastAPI(
        title="PyForge API",
        description="HTTP API for managing and executing jobs.",
        version="0.5.0",
    )

    job_manager = manager or JobManager(
        repository=SQLiteRepository("pyforge.db")
    )

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

    all_permissions = frozenset({"jobs:read","jobs:create","jobs:execute","jobs:delete",})
    reader_permissions = frozenset({"jobs:read",})
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

    return app


app = create_app()
