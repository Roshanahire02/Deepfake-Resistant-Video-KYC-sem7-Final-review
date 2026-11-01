"""Rate limiting, admin user management, and security headers."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core import rate_limit
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole
from app.tests.test_api import _auth_headers, _register_and_login


@pytest.fixture(scope="module", autouse=True)
def _db():
    Base.metadata.create_all(bind=engine)
    yield


def _make_user(role: UserRole, password="adminpass123"):
    email = f"{role.value.lower()}_{uuid.uuid4().hex[:6]}@example.com"
    db = SessionLocal()
    db.add(User(id=uuid.uuid4(), email=email, full_name=role.value.title(), password_hash=hash_password(password), role=role))
    db.commit()
    db.close()
    return email, password


def test_login_is_rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MIN", 3)
    rate_limit.reset()
    client = TestClient(app)
    codes = [client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrongpass1"}).status_code for _ in range(5)]
    assert codes[:3] == [401, 401, 401]
    assert codes[3] == 429 and codes[4] == 429
    rate_limit.reset()


def test_register_is_rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_MIN", 2)
    rate_limit.reset()
    client = TestClient(app)
    codes = [client.post("/api/auth/register", json={"email": f"rl{i}_{uuid.uuid4().hex[:5]}@example.com", "full_name": "X", "password": "testpass123"}).status_code for i in range(3)]
    assert codes == [201, 201, 429]
    rate_limit.reset()


def test_admin_endpoints_forbidden_for_non_admin():
    client = TestClient(app)
    _, token = _register_and_login(client)
    assert client.get("/api/admin/users", headers=_auth_headers(token)).status_code == 403
    assert client.get("/api/admin/users").status_code == 401


def test_admin_can_list_and_change_roles_but_not_own():
    client = TestClient(app)
    email, pw = _make_user(UserRole.ADMIN)
    admin_token = client.post("/api/auth/login", json={"email": email, "password": pw}).json()["access_token"]
    h = _auth_headers(admin_token)

    target_email, _ = _register_and_login(client)
    users = client.get("/api/admin/users", headers=h).json()
    target = next(u for u in users if u["email"] == target_email)
    assert target["role"] == "USER"

    r = client.put(f"/api/admin/users/{target['id']}/role", json={"role": "REVIEWER"}, headers=h)
    assert r.status_code == 200 and r.json()["role"] == "REVIEWER"
    assert client.put(f"/api/admin/users/{target['id']}/role", json={"role": "SUPERUSER"}, headers=h).status_code == 422

    me = next(u for u in users if u["email"] == email)
    assert client.put(f"/api/admin/users/{me['id']}/role", json={"role": "USER"}, headers=h).status_code == 400


def test_security_headers_present():
    r = TestClient(app).get("/api/system/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
