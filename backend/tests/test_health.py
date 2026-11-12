from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_reject_unsupported_file():
    response = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"not really an exe", "application/octet-stream")},
    )
    assert response.status_code == 415
