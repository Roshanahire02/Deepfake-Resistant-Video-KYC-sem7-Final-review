"""
Orchestrates the video-KYC stage of the pipeline (Objectives 2, 3, 4):
liveness -> deepfake -> replay -> face match -> fraud risk -> explanation.

Called after the document has already been uploaded/analyzed. The raw
video is only ever touched inside `video_service.process_and_cleanup_video`,
which guarantees deletion once this function returns.
"""
from __future__ import annotations

import uuid
from typing import List

import numpy as np
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services import progress
from app.ml.deepfake import analyze_video_frames
from app.ml.face_recognition import compare_faces
from app.ml.liveness import analyze_liveness
from app.ml.replay import analyze_replay
from app.ml.risk_engine import compute_risk
from app.ml.rppg import analyze_rppg
from app.models.document import Document
from app.models.kyc_case import CaseStatus, KYCCase
from app.models.results import (
    Decision,
    DeepfakeResult,
    FaceVerification,
    LivenessResult,
    ReplayResult,
    RiskAssessment,
    RiskLevel,
    RPPGResult,
)
from app.services.document_service import load_image_bgr


def _safe_call(fn, *args, **kwargs):
    """
    Runs an ML stage and, if its heavy optional dependency (torch /
    insightface / easyocr / mediapipe) isn't installed in this
    environment, returns an honest "dependency unavailable" result
    instead of crashing the whole video-KYC request. This never
    fabricates a score -- the affected fields are left as None and
    status is explicitly flagged, exactly like "Model unavailable" in
    the project spec.
    """
    try:
        return fn(*args, **kwargs), None
    except ImportError as exc:
        return None, str(exc)


def _upsert(db: Session, model, case_id, **fields):
    existing = db.query(model).filter(model.case_id == case_id).first()
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        db.add(existing)
        return existing
    obj = model(id=uuid.uuid4(), case_id=case_id, **fields)
    db.add(obj)
    return obj


def run_video_pipeline(
    db: Session,
    case: KYCCase,
    frames: List[np.ndarray],
    challenge_type: str,
    fps: float | None = None,
) -> dict:
    """
    Runs liveness, deepfake, replay and face-matching against the case's
    uploaded ID document, then computes the fraud risk score. Persists
    every stage's result. Returns the final risk assessment dict.
    """
    document = db.query(Document).filter(Document.case_id == case.id).order_by(Document.uploaded_at.desc()).first()
    if not document:
        raise HTTPException(status_code=400, detail="No identity document uploaded for this case yet.")

    ocr_result = case.ocr_result
    document_authenticity_score = ocr_result.authenticity_score if ocr_result else 0.0
    tampering_probability = ocr_result.tampering_probability if ocr_result else 1.0

    unavailable: dict = {}  # checks that could not run (reported honestly, never faked)
    progress.set_stage(case.id, "LIVENESS")
    # --- Liveness ---
    liveness, liveness_err = _safe_call(analyze_liveness, frames, challenge_type)
    if liveness is None:
        unavailable["liveness"] = "required library not installed"
        liveness = {"challenge_type": challenge_type, "passed": None, "motion_score": None,
                    "blink_count": None, "confidence": None, "status": "DEPENDENCY_UNAVAILABLE", "error": liveness_err}
    _upsert(
        db, LivenessResult, case.id,
        challenge_type=liveness.get("challenge_type"),
        passed=liveness.get("passed") if liveness.get("passed") is not None else False,
        motion_score=liveness.get("motion_score"),
        blink_count=liveness.get("blink_count"),
        confidence=liveness.get("confidence"),
    )

    progress.set_stage(case.id, "DEEPFAKE")
    # --- Deepfake ---
    deepfake, deepfake_err = _safe_call(analyze_video_frames, frames)
    if deepfake is None:
        deepfake = {"deepfake_probability": None, "status": "DEPENDENCY_UNAVAILABLE",
                    "frames_analyzed": 0, "suspicious_frame_indices": [], "model_version": "unavailable"}
    if deepfake.get("deepfake_probability") is None:
        unavailable["deepfake"] = {
            "TRAINING_REQUIRED": "model not trained",
            "NO_FACE_FRAMES": "no face found in sampled frames",
        }.get(deepfake.get("status"), "required library not installed")
    _upsert(
        db, DeepfakeResult, case.id,
        deepfake_probability=deepfake.get("deepfake_probability"),
        status=deepfake.get("status"),
        frames_analyzed=deepfake.get("frames_analyzed"),
        suspicious_frame_indices=deepfake.get("suspicious_frame_indices"),
        model_version=deepfake.get("model_version"),
    )

    progress.set_stage(case.id, "REPLAY")
    # --- Replay (pure OpenCV, no heavy optional dependency) ---
    replay = analyze_replay(frames)
    _upsert(
        db, ReplayResult, case.id,
        replay_probability=replay.get("replay_probability"),
        status=replay.get("status"),
        signals=replay.get("signals"),
    )

    progress.set_stage(case.id, "RPPG")
    # --- rPPG (physiological liveness signal) ---
    # Uses mediapipe (same optional dependency as liveness/face
    # detection) plus scipy for signal processing -- both go through
    # the same dependency-guard pattern as every other stage.
    rppg, rppg_err = _safe_call(analyze_rppg, frames, fps)
    if rppg is None:
        rppg = {
            "status": "UNAVAILABLE", "heart_rate_bpm": None, "signal_quality": None,
            "periodicity_score": None, "temporal_consistency": None, "usable_frames": 0,
            "usable_frame_ratio": None, "roi_stability": None, "rppg_score": None,
            "method": "CHROM", "message": f"DEPENDENCY_UNAVAILABLE: {rppg_err}",
        }
    _upsert(
        db, RPPGResult, case.id,
        status=rppg.get("status"),
        heart_rate_bpm=rppg.get("heart_rate_bpm"),
        signal_quality=rppg.get("signal_quality"),
        periodicity_score=rppg.get("periodicity_score"),
        temporal_consistency=rppg.get("temporal_consistency"),
        rppg_score=rppg.get("rppg_score"),
        usable_frames=rppg.get("usable_frames"),
        usable_frame_ratio=rppg.get("usable_frame_ratio"),
        roi_stability=rppg.get("roi_stability"),
        method_version=rppg.get("method"),
        message=rppg.get("message"),
    )

    progress.set_stage(case.id, "FACE_MATCH")
    # --- Face match: best/live frame vs ID document photo ---
    id_image = load_image_bgr(document.file_ref_temp)
    live_frame = frames[len(frames) // 2]  # a middle frame, avoids the very first/last (often blurry/transitional)
    face_result, face_err = _safe_call(compare_faces, live_frame, id_image)

    if face_result is None:
        unavailable["face_match"] = "face recognition library not installed"
        face_similarity, face_quality, match_status, multiple_faces, threshold = None, None, "DEPENDENCY_UNAVAILABLE", False, settings.FACE_MATCH_THRESHOLD
        _upsert(db, FaceVerification, case.id, similarity_score=None, match_status=f"DEPENDENCY_UNAVAILABLE: {face_err}",
                face_quality_score=None, multiple_faces_detected=False, threshold_used=threshold)
    elif "error" in face_result:
        face_similarity, face_quality, match_status, multiple_faces, threshold = 0.0, 0.0, "NOT_MATCHED", False, settings.FACE_MATCH_THRESHOLD
        _upsert(db, FaceVerification, case.id, similarity_score=0.0, match_status="ERROR: " + face_result["error"],
                face_quality_score=0.0, multiple_faces_detected=False, threshold_used=threshold)
    else:
        face_similarity = face_result["similarity_score"]
        face_quality = face_result["face_quality_score"]
        match_status = face_result["match_status"]
        multiple_faces = face_result["multiple_faces_detected"]
        threshold = face_result["threshold_used"]
        _upsert(
            db, FaceVerification, case.id,
            similarity_score=face_similarity,
            match_status=match_status,
            face_quality_score=face_quality,
            multiple_faces_detected=multiple_faces,
            threshold_used=threshold,
        )

    db.commit()

    # --- Fraud risk engine ---
    risk_features = {
        "document_authenticity_score": document_authenticity_score or 0.0,
        "tampering_probability": tampering_probability or 0.0,
        "face_similarity": face_similarity,
        "face_quality": face_quality,
        "liveness_passed": bool(liveness.get("passed")),
        "deepfake_probability": deepfake.get("deepfake_probability"),
        "replay_probability": replay.get("replay_probability") or 0.0,
    }
    progress.set_stage(case.id, "RISK")
    risk = compute_risk(risk_features, rppg=rppg, unavailable=unavailable)

    _upsert(
        db, RiskAssessment, case.id,
        fraud_risk_score=risk["fraud_risk_score"],
        risk_level=RiskLevel(risk["risk_level"]),
        decision=Decision(risk["decision"]),
        feature_contributions=risk["feature_contributions"],
        explanation_text=risk["explanation_text"],
        model_version=risk["model_version"],
    )

    case.status = {
        "VERIFIED": CaseStatus.VERIFIED,
        "MANUAL_REVIEW": CaseStatus.MANUAL_REVIEW,
        "FLAGGED": CaseStatus.FLAGGED,
    }.get(risk["decision"], CaseStatus.RISK_CALCULATED)
    db.add(case)
    db.commit()

    return {
        "liveness": liveness,
        "deepfake": deepfake,
        "replay": replay,
        "rppg": rppg,
        "face": {
            "similarity_score": face_similarity,
            "match_status": match_status,
            "face_quality_score": face_quality,
            "multiple_faces_detected": multiple_faces,
            "threshold_used": threshold,
        },
        "risk": risk,
    }
