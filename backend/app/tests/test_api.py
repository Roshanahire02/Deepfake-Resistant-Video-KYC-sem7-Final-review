"""
Backend test suite.

Uses a throwaway SQLite database (separate from the dev .env database)
so tests never touch real data, and FastAPI's TestClient for real
HTTP-level requests through the actual routing/dependency stack.

Run with (from backend/, venv active):
    pytest -v
"""
from __future__ import annotations

import os
import uuid

import numpy as np
import cv2
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./storage/test.db"

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import document, kyc_case, results, user  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    if os.path.exists("./storage/test.db"):
        os.remove("./storage/test.db")
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


def _unique_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"


def _register_and_login(client, email=None, password="testpass123"):
    email = email or _unique_email()
    r = client.post("/api/auth/register", json={"email": email, "full_name": "Test User", "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return email, token


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- auth ----

def test_register_and_login(client):
    email, token = _register_and_login(client)
    assert token
    r = client.get("/api/auth/me", headers=_auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == email
    assert r.json()["role"] == "USER"


def test_duplicate_registration_rejected(client):
    email, _ = _register_and_login(client)
    r = client.post("/api/auth/register", json={"email": email, "full_name": "Dup", "password": "testpass123"})
    assert r.status_code == 400


def test_wrong_password_rejected(client):
    email, _ = _register_and_login(client)
    r = client.post("/api/auth/login", json={"email": email, "password": "wrong-password"})
    assert r.status_code == 401


def test_unauthenticated_request_rejected(client):
    r = client.post("/api/kyc/create")
    assert r.status_code == 401


# --------------------------------------------------------- kyc case flow --

def test_create_case_and_list(client):
    _, token = _register_and_login(client)
    r = client.post("/api/kyc/create", headers=_auth_headers(token))
    assert r.status_code == 201
    case_id = r.json()["id"]
    assert r.json()["status"] == "CREATED"

    r = client.get("/api/kyc/list", headers=_auth_headers(token))
    assert r.status_code == 200
    assert any(c["id"] == case_id for c in r.json())


def test_case_ownership_enforced(client):
    _, token_a = _register_and_login(client)
    _, token_b = _register_and_login(client)

    case_id = client.post("/api/kyc/create", headers=_auth_headers(token_a)).json()["id"]

    r = client.get(f"/api/kyc/{case_id}", headers=_auth_headers(token_b))
    assert r.status_code == 403

    r = client.get(f"/api/kyc/{case_id}", headers=_auth_headers(token_a))
    assert r.status_code == 200


def _make_test_document_bytes() -> bytes:
    img = np.full((300, 500, 3), 255, dtype=np.uint8)
    cv2.putText(img, "SAMPLE ID", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_document_upload_and_analyze(client):
    _, token = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(token)).json()["id"]

    files = {"file": ("id.jpg", _make_test_document_bytes(), "image/jpeg")}
    r = client.post("/api/kyc/document/upload", data={"case_id": case_id}, files=files, headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    document_id = r.json()["document_id"]
    assert r.json()["case_status"] == "DOCUMENT_UPLOADED"

    r = client.post(
        "/api/kyc/document/analyze",
        data={"case_id": case_id, "document_id": document_id},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Tampering analysis has no heavy optional dependency -- always real.
    assert body["authenticity_score"] is not None
    assert 0 <= body["authenticity_score"] <= 100
    assert isinstance(body["tampering_flag"], bool)
    # OCR fields may legitimately be None if easyocr isn't installed in
    # this environment -- that's honest degradation, not a failure.


def test_rejects_unsupported_file_type(client):
    _, token = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(token)).json()["id"]
    files = {"file": ("doc.txt", b"not an image", "text/plain")}
    r = client.post("/api/kyc/document/upload", data={"case_id": case_id}, files=files, headers=_auth_headers(token))
    assert r.status_code == 400


# ----------------------------------------------------------- reviewer -----

def test_reviewer_endpoints_forbidden_for_plain_user(client):
    _, token = _register_and_login(client)
    r = client.get("/api/reviewer/cases", headers=_auth_headers(token))
    assert r.status_code == 403


def test_reviewer_can_list_and_decide(client):
    # applicant creates + analyzes a case
    _, applicant_token = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(applicant_token)).json()["id"]
    files = {"file": ("id.jpg", _make_test_document_bytes(), "image/jpeg")}
    upload = client.post(
        "/api/kyc/document/upload", data={"case_id": case_id}, files=files, headers=_auth_headers(applicant_token)
    ).json()
    client.post(
        "/api/kyc/document/analyze",
        data={"case_id": case_id, "document_id": upload["document_id"]},
        headers=_auth_headers(applicant_token),
    )

    # promote a second account to REVIEWER directly via the DB (mirrors
    # app/scripts/seed_reviewer.py, done inline here to keep the test hermetic)
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    db = SessionLocal()
    reviewer_email = _unique_email()
    reviewer = User(
        id=uuid.uuid4(), email=reviewer_email, full_name="Reviewer",
        password_hash=hash_password("reviewpass123"), role=UserRole.REVIEWER,
    )
    db.add(reviewer)
    db.commit()
    db.close()

    r = client.post("/api/auth/login", json={"email": reviewer_email, "password": "reviewpass123"})
    reviewer_token = r.json()["access_token"]

    r = client.get("/api/reviewer/cases", headers=_auth_headers(reviewer_token))
    assert r.status_code == 200
    assert any(c["case_id"] == case_id for c in r.json())

    r = client.put(
        f"/api/reviewer/cases/{case_id}/decision",
        json={"action": "MANUAL_REVIEW", "notes": "test note"},
        headers=_auth_headers(reviewer_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["new_status"] == "MANUAL_REVIEW"


# ------------------------------------------------------------- system -----

def test_system_health(client):
    r = client.get("/api/system/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_system_models_never_fabricates_loaded_status(client):
    r = client.get("/api/system/models")
    assert r.status_code == 200
    body = r.json()
    names = [m["model"] for m in body]
    assert "Fraud Risk Engine" in names
    for m in body:
        assert "status" in m and m["status"]


# ------------------------------------------------------------- PDF --------

def _make_test_pdf_bytes() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=500, height=300)
    page.insert_text((30, 60), "SAMPLE ID CARD", fontsize=24)
    page.insert_text((30, 120), "Name: JOHN TEST DOE", fontsize=14)
    data = doc.tobytes()
    doc.close()
    return data


def test_pdf_upload_and_analyze_renders_first_page(client):
    _, token = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(token)).json()["id"]
    files = {"file": ("id.pdf", _make_test_pdf_bytes(), "application/pdf")}
    r = client.post("/api/kyc/document/upload", data={"case_id": case_id}, files=files, headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    r = client.post(
        "/api/kyc/document/analyze",
        data={"case_id": case_id, "document_id": r.json()["document_id"]},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["authenticity_score"] is not None  # tampering analysis ran on the rendered page


def test_fake_pdf_content_rejected(client):
    _, token = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(token)).json()["id"]
    files = {"file": ("evil.pdf", b"this is not really a pdf", "application/pdf")}
    r = client.post("/api/kyc/document/upload", data={"case_id": case_id}, files=files, headers=_auth_headers(token))
    assert r.status_code == 400
