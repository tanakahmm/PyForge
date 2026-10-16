
from fastapi.testclient import TestClient

from pyforge.api import create_app
from pyforge.engine.manager import JobManager
from pyforge.storage.memory_repository import MemoryRepository
from pyforge.storage.sqlite_schedule_repository import (
    SQLiteScheduleRepository,
)


def make_app():
    manager = JobManager(repository=MemoryRepository())
    schedule_repository = SQLiteScheduleRepository(":memory:")

    return create_app(
        manager=manager,
        api_key="test-admin",
        readonly_api_key="test-reader",
        schedule_repository=schedule_repository,
    )


def test_create_and_list_schedule():
    app = make_app()

    with TestClient(app) as client:
        admin = {"X-API-Key": "test-admin"}

        job_response = client.post(
            "/jobs",
            headers=admin,
            json={
                "name": "scheduled-demo",
                "command": ["python3", "-c", "print('hello')"],
            },
        )
        assert job_response.status_code == 201
        job_id = job_response.json()["id"]

        response = client.post(
            "/schedules",
            headers=admin,
            json={
                "job_id": job_id,
                "interval_seconds": 3600,
            },
        )

        assert response.status_code == 201
        schedule = response.json()
        assert schedule["job_id"] == job_id
        assert schedule["interval_seconds"] == 3600
        assert schedule["enabled"] is True

        listed = client.get("/schedules", headers=admin)
        assert listed.status_code == 200
        assert any(
            item["id"] == schedule["id"]
            for item in listed.json()
        )


def test_reader_can_list_but_cannot_create_schedule():
    app = make_app()

    with TestClient(app) as client:
        reader = {"X-API-Key": "test-reader"}

        response = client.get("/schedules", headers=reader)
        assert response.status_code == 200

        denied = client.post(
            "/schedules",
            headers=reader,
            json={
                "job_id": "unknown",
                "interval_seconds": 3600,
            },
        )
        assert denied.status_code == 403


def test_schedule_enable_disable_and_delete():
    app = make_app()

    with TestClient(app) as client:
        admin = {"X-API-Key": "test-admin"}

        job = client.post(
            "/jobs",
            headers=admin,
            json={
                "name": "lifecycle",
                "command": ["python3", "-c", "pass"],
            },
        ).json()

        schedule = client.post(
            "/schedules",
            headers=admin,
            json={
                "job_id": job["id"],
                "interval_seconds": 3600,
            },
        ).json()
        schedule_id = schedule["id"]

        disabled = client.post(
            f"/schedules/{schedule_id}/disable",
            headers=admin,
        )
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False

        enabled = client.post(
            f"/schedules/{schedule_id}/enable",
            headers=admin,
        )
        assert enabled.status_code == 200
        assert enabled.json()["enabled"] is True

        deleted = client.delete(
            f"/schedules/{schedule_id}",
            headers=admin,
        )
        assert deleted.status_code == 204

        missing = client.get(
            f"/schedules/{schedule_id}",
            headers=admin,
        )
        assert missing.status_code == 404


def test_schedule_rejects_invalid_interval():
    app = make_app()

    with TestClient(app) as client:
        admin = {"X-API-Key": "test-admin"}

        response = client.post(
            "/schedules",
            headers=admin,
            json={
                "job_id": "does-not-matter",
                "interval_seconds": 0,
            },
        )

        assert response.status_code == 422
