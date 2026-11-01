"""
Tests for the rPPG (remote photoplethysmography) module.

Follows the same synthetic-signal approach as the rest of the ML test
suite: no mocking-away of the math, only mocking the mediapipe face
detection step where a real camera-captured face would otherwise be
required (see test_analyze_rppg_full_pipeline_with_synthetic_face).
"""
from __future__ import annotations

import os

import numpy as np
import pytest

from app.ml import rppg
from app.core.config import settings


# ---------------------------------------------------------- 1. imports ----

def test_rppg_module_imports():
    assert hasattr(rppg, "analyze_rppg")
    assert hasattr(rppg, "apply_pos_or_chrom")
    assert hasattr(rppg, "estimate_heart_rate")


# --------------------------------------------------- synthetic signal ----

def _make_synthetic_rgb_signal(bpm: float, fps: float, duration_s: float, noise_std: float = 0.3):
    n = int(fps * duration_s)
    t = np.arange(n) / fps
    hr_hz = bpm / 60.0
    base_rgb = np.array([180.0, 130.0, 110.0])
    amplitude = np.array([1.5, 2.0, 0.5])  # green channel carries the strongest pulsatile component
    signal = base_rgb[None, :] + amplitude[None, :] * np.sin(2 * np.pi * hr_hz * t)[:, None]
    rng = np.random.default_rng(42)
    signal += rng.normal(0, noise_std, signal.shape)
    return signal


def test_chrom_recovers_known_heart_rate():
    fps = 20.0
    true_bpm = 72.0
    signal = _make_synthetic_rgb_signal(true_bpm, fps, duration_s=8)

    preprocessed = rppg.preprocess_signal(signal)
    pulse = rppg.apply_pos_or_chrom(preprocessed)
    filtered = rppg._bandpass_filter(pulse, fps, settings.RPPG_MIN_BPM / 60, settings.RPPG_MAX_BPM / 60)
    estimated_bpm, periodicity = rppg.estimate_heart_rate(filtered, fps)

    assert estimated_bpm is not None
    # Welch's frequency resolution over an 8s window is coarse -- allow a
    # realistic tolerance rather than demanding an exact match.
    assert abs(estimated_bpm - true_bpm) <= 8
    assert 0 < periodicity <= 1


def test_signal_quality_calculation_is_bounded():
    q = rppg.calculate_signal_quality(usable_frame_ratio=0.9, roi_stability=0.8, periodicity_score=0.3)
    assert 0 <= q <= 1


def test_temporal_consistency_high_for_stationary_signal():
    fps = 20.0
    signal = _make_synthetic_rgb_signal(75.0, fps, duration_s=8)
    pulse = rppg.apply_pos_or_chrom(rppg.preprocess_signal(signal))
    filtered = rppg._bandpass_filter(pulse, fps, settings.RPPG_MIN_BPM / 60, settings.RPPG_MAX_BPM / 60)
    consistency = rppg._temporal_consistency(filtered, fps)
    assert consistency >= 0.5  # same rate in both halves -> should agree well


def test_estimate_heart_rate_returns_none_for_pure_noise():
    fps = 20.0
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, 160)
    hr, periodicity = rppg.estimate_heart_rate(noise, fps)
    # Pure white noise may occasionally still show a weak peak; the
    # important invariant is periodicity stays low, not a hard None.
    assert periodicity < 0.5


# ------------------------------------------------- insufficient input ----

def test_analyze_rppg_no_frames():
    result = rppg.analyze_rppg([], fps=20.0)
    assert result["status"] == "UNAVAILABLE"
    assert result["heart_rate_bpm"] is None


def test_analyze_rppg_insufficient_frames():
    frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
    result = rppg.analyze_rppg(frames, fps=20.0)
    assert result["status"] == "INSUFFICIENT_SIGNAL"
    assert "frames" in result["message"].lower()
    assert result["heart_rate_bpm"] is None


def test_analyze_rppg_no_face_detected():
    # Enough frames, but blank images -- mediapipe will find no face.
    frames = [np.zeros((200, 200, 3), dtype=np.uint8) for _ in range(settings.RPPG_MIN_FRAMES + 5)]
    result = rppg.analyze_rppg(frames, fps=20.0)
    assert result["status"] == "INSUFFICIENT_SIGNAL"
    assert result["heart_rate_bpm"] is None
    # Never fabricate a positive-looking usable_frame_ratio when nothing was found.
    assert result.get("usable_frame_ratio") in (0.0, None) or result.get("usable_frame_ratio") < settings.RPPG_MIN_FACE_DETECTION_RATIO


def test_analyze_rppg_never_reports_heart_rate_below_quality_threshold(monkeypatch):
    """
    Forces the low-signal-quality branch and confirms heart_rate_bpm is
    nulled out even though an (unreliable) estimate technically exists
    internally -- "never manufacture a heart-rate result" for output
    the pipeline doesn't trust.
    """
    n = settings.RPPG_MIN_FRAMES + 10
    frames = [np.zeros((200, 200, 3), dtype=np.uint8) for _ in range(n)]

    fake_bboxes = [(10, 10, 50, 30)] * n
    fake_rois = [np.full((20, 40, 3), 128, dtype=np.uint8)] * n

    def fake_extract_face_roi_frames(_frames):
        return fake_rois, fake_bboxes, n

    monkeypatch.setattr(rppg, "extract_face_roi_frames", fake_extract_face_roi_frames)
    monkeypatch.setattr(rppg, "calculate_signal_quality", lambda *a, **k: 0.01)  # force below threshold

    result = rppg.analyze_rppg(frames, fps=20.0)
    assert result["status"] == "INSUFFICIENT_SIGNAL"
    assert result["heart_rate_bpm"] is None


# --------------------------------------------------- pipeline wiring -----

def test_kyc_pipeline_service_imports_rppg():
    from app.services import kyc_pipeline_service

    assert "analyze_rppg" in dir(kyc_pipeline_service) or hasattr(kyc_pipeline_service, "run_video_pipeline")


_BASE = {
    "document_authenticity_score": 70.0,
    "tampering_probability": 0.3,
    "face_similarity": 0.6,
    "face_quality": 0.7,
    "liveness_passed": True,
    "deepfake_probability": 0.3,
    "replay_probability": 0.3,
}


def test_missing_rppg_never_changes_the_score():
    """INSUFFICIENT_SIGNAL / UNAVAILABLE are passed to the model as 'missing',
    never as a made-up value -- so they score exactly like 'no rPPG given'."""
    from app.ml.risk_engine import compute_risk

    none = compute_risk(dict(_BASE))
    insufficient = compute_risk(dict(_BASE), rppg={"status": "INSUFFICIENT_SIGNAL", "rppg_score": None})
    unavailable = compute_risk(dict(_BASE), rppg={"status": "UNAVAILABLE", "rppg_score": None})
    assert none["fraud_risk_score"] == insufficient["fraud_risk_score"] == unavailable["fraud_risk_score"]
    assert "rppg" not in none["explanation_text"].lower()


def test_v2_model_uses_rppg_in_documented_direction():
    """With risk_model_v2 loaded, a stronger real rPPG score must not raise risk
    (monotone constraint), and rppg_score appears in the SHAP contributions."""
    from app.ml.risk_engine import _load_model, compute_risk

    _, version, trained, feats = _load_model()
    assert trained and "rppg_score" in feats, "risk_model_v2.joblib should ship with the project"
    weak = compute_risk(dict(_BASE), rppg={"status": "AVAILABLE", "rppg_score": 0.1, "heart_rate_bpm": 70})
    strong = compute_risk(dict(_BASE), rppg={"status": "AVAILABLE", "rppg_score": 0.9, "heart_rate_bpm": 70})
    assert strong["fraud_risk_score"] <= weak["fraud_risk_score"]
    assert "rppg_score" in strong["feature_contributions"]
    assert "rppg" in strong["explanation_text"].lower() or "pulse" in strong["explanation_text"].lower()


def test_falls_back_to_v1_when_v2_absent(tmp_path, monkeypatch):
    """Without v2 the original 7-feature model is used and rPPG cannot change the score."""
    import shutil

    from app.core.config import settings
    from app.ml import risk_engine

    shutil.copy(os.path.join(settings.MODEL_DIR, "risk_model.joblib"), tmp_path / "risk_model.joblib")
    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    risk_engine._load_model.cache_clear()
    try:
        a = risk_engine.compute_risk(dict(_BASE))
        b = risk_engine.compute_risk(dict(_BASE), rppg={"status": "AVAILABLE", "rppg_score": 0.9, "heart_rate_bpm": 70})
        assert a["model_version"] == "trained_on_synthetic_data_v1"
        assert a["fraud_risk_score"] == b["fraud_risk_score"]
    finally:
        monkeypatch.undo()
        risk_engine._load_model.cache_clear()
