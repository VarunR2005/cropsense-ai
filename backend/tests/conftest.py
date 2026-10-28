import os

# Must be set BEFORE importing the app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["OPENWEATHER_API_KEY"] = ""  # tests must never call the real weather API
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-0123456789"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app import models  # noqa: F401


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    client.post("/api/auth/register", json={
        "full_name": "Test Farmer", "email": "farmer@example.com", "password": "password123"})
    r = client.post("/api/auth/login", data={"username": "farmer@example.com", "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
