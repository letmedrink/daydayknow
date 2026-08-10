from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_global_and_project_routes(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            created = client.post("/api/projects", json={"name": "alpha"})
            assert created.status_code == 200
            project_id = created.json()["data"]["id"]

            assert client.get("/api/settings").status_code == 200
            assert client.get("/api/profile").status_code == 200
            pages = client.get(f"/api/projects/{project_id}/wiki/pages")
            assert pages.status_code == 200
            assert pages.json()["data"] == {"tree": [], "pages": []}
    finally:
        settings.DATA_DIR = original_data_dir


def test_missing_project_uses_error_envelope(tmp_path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        with TestClient(app) as client:
            response = client.get("/api/projects/missing/wiki/pages")
            assert response.status_code == 404
            assert response.json()["success"] is False
            assert response.json()["code"] == "http_error"
    finally:
        settings.DATA_DIR = original_data_dir
