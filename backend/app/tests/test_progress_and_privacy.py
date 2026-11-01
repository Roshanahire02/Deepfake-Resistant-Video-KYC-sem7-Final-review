"""Real pipeline progress + the 'raw video is deleted' privacy guarantee."""
from __future__ import annotations

import os
import uuid

import cv2
import numpy as np
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./storage/test.db"

import pytest  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.utils.temp_file_manager import ensure_dirs  # noqa: E402
from app.main import app  # noqa: E402
from app.services import progress  # noqa: E402
from app.tests.test_api import _auth_headers, _make_test_document_bytes, _register_and_login  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _db():
    ensure_dirs()
    Base.metadata.create_all(bind=engine)
    yield


def test_progress_module_tracks_stages_in_order():
    cid = uuid.uuid4()
    progress.start(cid)
    progress.set_stage(cid, "LIVENESS")
    progress.set_stage(cid, "DEEPFAKE")
    info = progress.get(cid)
    assert info["stage"] == "DEEPFAKE" and info["state"] == "RUNNING"
    assert info["completed"] == ["EXTRACTING_FRAMES", "LIVENESS"]
    progress.finish(cid, ok=True)
    assert progress.get(cid)["state"] == "DONE"
    assert "DEEPFAKE" in progress.get(cid)["completed"]


def test_progress_endpoint_idle_and_ownership():
    client = TestClient(app)
    _, ta = _register_and_login(client)
    _, tb = _register_and_login(client)
    case_id = client.post("/api/kyc/create", headers=_auth_headers(ta)).json()["id"]
    r = client.get(f"/api/kyc/{case_id}/progress", headers=_auth_headers(ta))
    assert r.status_code == 200 and r.json()["state"] == "IDLE"
    assert client.get(f"/api/kyc/{case_id}/progress", headers=_auth_headers(tb)).status_code == 403
    assert client.get(f"/api/kyc/{case_id}/progress").status_code == 401


def _synthetic_video_bytes(tmp_path) -> bytes:
    path = str(tmp_path / "v.mp4")
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (320, 240))
    for _ in range(50):
        out.write(np.full((240, 320, 3), 200, dtype=np.uint8))
    out.release()
    return open(path, "rb").read()


def test_video_pipeline_reports_done_and_deletes_raw_video(tmp_path):
    client = TestClient(app)
    _, token = _register_and_login(client)
    h = _auth_headers(token)
    case_id = client.post("/api/kyc/create", headers=h).json()["id"]
    up = client.post("/api/kyc/document/upload", data={"case_id": case_id},
                     files={"file": ("id.jpg", _make_test_document_bytes(), "image/jpeg")}, headers=h).json()
    client.post("/api/kyc/document/analyze", data={"case_id": case_id, "document_id": up["document_id"]}, headers=h)

    r = client.post("/api/kyc/video/process",
                    data={"case_id": case_id, "challenge_type": "BLINK_TWICE", "consent": "true"},
                    files={"file": ("v.mp4", _synthetic_video_bytes(tmp_path), "video/mp4")}, headers=h)
    assert r.status_code == 200, r.text
    assert {"liveness", "deepfake", "replay", "rppg", "face", "risk"} <= set(r.json())

    info = client.get(f"/api/kyc/{case_id}/progress", headers=h).json()
    assert info["state"] == "DONE"
    assert set(info["stages"]) == set(info["completed"])  # every real stage ran

    leftover = [f for f in os.listdir(settings.TEMP_VIDEO_DIR) if not f.startswith(".")]
    assert leftover == [], f"raw video not deleted: {leftover}"


def test_video_requires_consent():
    client = TestClient(app)
    _, token = _register_and_login(client)
    h = _auth_headers(token)
    case_id = client.post("/api/kyc/create", headers=h).json()["id"]
    r = client.post("/api/kyc/video/process", data={"case_id": case_id, "challenge_type": "BLINK_TWICE", "consent": "false"},
                    files={"file": ("v.mp4", b"x", "video/mp4")}, headers=h)
    assert r.status_code == 400


def test_startup_purge_removes_leftover_temp_videos(tmp_path, monkeypatch):
    from app.utils.temp_file_manager import purge_temp_videos

    monkeypatch.setattr(settings, "TEMP_VIDEO_DIR", str(tmp_path))
    (tmp_path / "leftover1.webm").write_bytes(b"x")
    (tmp_path / "leftover2.mp4").write_bytes(b"y")
    (tmp_path / ".gitkeep").write_bytes(b"")
    assert purge_temp_videos() == 2
    assert sorted(os.listdir(tmp_path)) == [".gitkeep"]


def test_delete_path_reports_failure_loudly_not_silently(tmp_path, monkeypatch):
    """If a file can't be deleted, delete_path must return False (and log an error)."""
    from app.utils import temp_file_manager as tfm

    f = tmp_path / "locked.webm"
    f.write_bytes(b"x")

    def locked(_p):
        raise PermissionError("file is in use")

    monkeypatch.setattr(tfm.os, "remove", locked)
    assert tfm.delete_path(str(f), attempts=2, delay=0) is False
