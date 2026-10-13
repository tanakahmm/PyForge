
from fastapi.testclient import TestClient

from pyforge.api import create_app
from pyforge.engine.manager import JobManager
from pyforge.storage.memory_repository import MemoryRepository


def make_client():
    manager = JobManager(repository=MemoryRepository())
    app = create_app(manager,api_key="test-secret")
    return TestClient(app,headers={"X-API-Key": "test-secret"},)


def test_health_endpoint():
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_and_get_job():
    client = make_client()

    response = client.post(
        "/jobs",
        json={
            "name": "hello",
            "command": ["python3", "-c", "print('hello')"],
            "timeout": 10,
        },
    )

    assert response.status_code == 201
    job = response.json()
    assert job["name"] == "hello"
    assert job["status"] == "pending"

    fetched = client.get(f"/jobs/{job['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == job["id"]


def test_create_job_rejects_empty_command():
    client = make_client()

    response = client.post(
        "/jobs",
        json={"name": "invalid", "command": []},
    )

    assert response.status_code == 422


def test_missing_job_returns_404():
    client = make_client()

    response = client.get("/jobs/does-not-exist")

    assert response.status_code == 404


def test_run_job_and_get_result():
    client = make_client()

    created = client.post(
        "/jobs",
        json={
            "name": "hello",
            "command": ["python3", "-c", "print('hello')"],
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    result = client.post(f"/jobs/{job_id}/run")
    assert result.status_code == 200
    assert result.json()["status"] == "success"
    assert "hello" in result.json()["stdout"]

    fetched = client.get(f"/jobs/{job_id}/result")
    assert fetched.status_code == 200
    assert fetched.json()["job_id"] == job_id


def test_delete_job():
    client = make_client()

    created = client.post(
        "/jobs",
        json={
            "name": "delete-me",
            "command": ["python3", "-c", "pass"],
        },
    )
    job_id = created.json()["id"]

    deleted = client.delete(f"/jobs/{job_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/jobs/{job_id}")
    assert missing.status_code == 404

def test_missing_api_key_is_rejected():
    app = create_app(
        JobManager(repository=MemoryRepository()),
        api_key="test-secret",
    )
    client = TestClient(app)

    response = client.get("/jobs")

    assert response.status_code == 401


def test_invalid_api_key_is_rejected():
    app = create_app(
        JobManager(repository=MemoryRepository()),
        api_key="test-secret",
    )
    client = TestClient(
        app,
        headers={"X-API-Key": "wrong-secret"},
    )

    response = client.get("/jobs")

    assert response.status_code == 401