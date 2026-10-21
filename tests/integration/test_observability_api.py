from fastapi.testclient import TestClient

from pyforge.api import create_app
from pyforge.engine.manager import JobManager
from pyforge.storage.memory_repository import MemoryRepository
from pyforge.storage.sqlite_schedule_repository import (
    SQLiteScheduleRepository,
)


def build_app():
    manager = JobManager(repository=MemoryRepository())
    schedule_repository = SQLiteScheduleRepository(":memory:")

    return create_app(
        manager=manager,
        api_key="test-admin",
        readonly_api_key="test-reader",
        schedule_repository=schedule_repository,
    )


def test_health_response_includes_request_id():
    app = build_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_readiness_endpoint():
    app = build_app()

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_metrics_endpoint_requires_authentication():
    app = build_app()

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 401


def test_admin_can_read_metrics():
    app = build_app()

    with TestClient(app) as client:
        response = client.get(
            "/metrics",
            headers={"X-API-Key": "test-admin"},
        )

    assert response.status_code == 200
    assert "pyforge_http_requests_total" in response.text
    assert "pyforge_http_request_duration_seconds" in response.text