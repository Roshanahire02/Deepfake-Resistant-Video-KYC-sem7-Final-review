"""
Unavailable checks must be reported as unavailable -- never turned into a
made-up number, never crash scoring, and never allow auto-VERIFIED when a
required check (face match / liveness) could not run.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, engine
from app.main import app
from app.ml import deepfake
from app.ml.risk_engine import compute_risk
from app.tests.test_api import _auth_headers, _make_test_document_bytes, _register_and_login

GOOD = {
    "document_authenticity_score": 95.0, "tampering_probability": 0.02, "face_similarity": 0.95,
    "face_quality": 0.9, "liveness_passed": True, "deepfake_probability": 0.02, "replay_probability": 0.02,
}


@pytest.fixture(scope="module", autouse=True)
def _db():
    Base.metadata.create_all(bind=engine)
    yield


def test_deepfake_without_checkpoint_reports_training_required_and_no_probability(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))  # no deepfake_effnet.pt here
    frames = [np.zeros((64, 64, 3), np.uint8) for _ in range(20)]
    r = deepfake.analyze_video_frames(frames)
    assert r["status"] == "TRAINING_REQUIRED"
    assert r["deepfake_probability"] is None
    assert r["frames_analyzed"] == 0 and r["suspicious_frame_indices"] == []


def test_unavailable_deepfake_is_disclosed_not_scored_as_zero():
    out = compute_risk({**GOOD, "deepfake_probability": None}, unavailable={"deepfake": "model not trained"})
    assert "deepfake" in out["explanation_text"].lower() and "could not be evaluated" in out["explanation_text"]
    assert out["unavailable_signals"] == {"deepfake": "model not trained"}


def test_unavailable_face_match_does_not_crash_and_blocks_auto_verification():
    out = compute_risk({**GOOD, "face_similarity": None, "face_quality": None}, unavailable={"face_match": "library missing"})
    assert out["decision"] != "VERIFIED"
    assert "withheld" in out["explanation_text"]


def test_unavailable_liveness_blocks_auto_verification():
    out = compute_risk(dict(GOOD), unavailable={"liveness": "library missing"})
    assert out["decision"] != "VERIFIED"


def test_all_checks_available_can_still_verify():
    out = compute_risk(dict(GOOD))
    assert out["unavailable_signals"] == {}
    assert out["decision"] == "VERIFIED"


def test_pipeline_survives_missing_face_recognition_library(tmp_path, monkeypatch):
    """The latent crash: face recognition lib missing (ImportError) while a face
    exists used to put None into the risk engine. Must now degrade honestly."""
    from app.services import kyc_pipeline_service as svc

    def boom(*a, **k):
        raise ImportError("No module named 'insightface'")

    monkeypatch.setattr(svc, "compare_faces", boom)

    client = TestClient(app)
    _, token = _register_and_login(client)
    h = _auth_headers(token)
    case_id = client.post("/api/kyc/create", headers=h).json()["id"]
    up = client.post("/api/kyc/document/upload", data={"case_id": case_id},
                     files={"file": ("id.jpg", _make_test_document_bytes(), "image/jpeg")}, headers=h).json()
    client.post("/api/kyc/document/analyze", data={"case_id": case_id, "document_id": up["document_id"]}, headers=h)

    path = str(tmp_path / "v.mp4")
    out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (320, 240))
    for _ in range(50):
        out.write(np.full((240, 320, 3), 200, np.uint8))
    out.release()

    r = client.post("/api/kyc/video/process", data={"case_id": case_id, "challenge_type": "BLINK_TWICE", "consent": "true"},
                    files={"file": ("v.mp4", open(path, "rb").read(), "video/mp4")}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["risk"]["decision"] != "VERIFIED"
    assert "face_match" in body["risk"]["unavailable_signals"]
    assert body["deepfake"]["deepfake_probability"] is None  # no checkpoint => no fabricated number

    # the recalculation endpoint agrees with the live pipeline
    rc = client.post("/api/kyc/risk/calculate", data={"case_id": case_id}, headers=h)
    assert rc.status_code == 200, rc.text
    assert rc.json()["fraud_risk_score"] == body["risk"]["fraud_risk_score"]
    assert [f for f in os.listdir(settings.TEMP_VIDEO_DIR) if not f.startswith('.')] == []
