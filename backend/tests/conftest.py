import os

os.environ["CAREERPILOT_TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["LLM_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import engine
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "llm_api_key", "")
    with TestClient(app) as test_client:
        yield test_client


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, email: str = "user@example.com", password: str = "secret123") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "confirm_password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()
