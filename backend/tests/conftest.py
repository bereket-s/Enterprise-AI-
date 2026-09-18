import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app


@pytest.fixture()
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # app/core/scheduler.py and app/core/middleware.py both open their own
    # SessionLocal() outside any request's get_db() dependency (a background
    # tick and a request-logging middleware, neither of which can depend-inject
    # a session) — without these patches they would silently talk to the *real*
    # app database (backend/platform.db) on every test run instead of this
    # test's isolated in-memory one, which is both wrong for the tests and
    # unsafe for the real demo data the report's numbers were generated from.
    import app.core.database as database_module
    import app.core.scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(database_module, "SessionLocal", TestingSessionLocal)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_org(client):
    payload = {
        "organization": {"name": "Acme Test Co", "industry": "retail", "size": "51-200", "country": "US"},
        "admin_email": "admin@acme-test.com",
        "admin_password": "SuperSecret123",
        "admin_full_name": "Ada Admin",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return payload


@pytest.fixture()
def auth_headers(client, registered_org):
    resp = client.post(
        "/api/auth/login",
        data={"username": registered_org["admin_email"], "password": registered_org["admin_password"]},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
