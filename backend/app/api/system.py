"""
GET /api/system/models

Reports the real, current status of every ML component. Never
fabricates "Loaded"/accuracy claims -- statuses are derived from
whether an actual checkpoint file exists on disk, exactly as the
inference modules themselves check.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])

NOT_EVALUATED = {"state": "NOT_EVALUATED", "summary": "Not evaluated yet"}


def _evaluation(checkpoint_filename: str, synthetic: bool = False) -> dict:
    """Reads <checkpoint>.metrics.json written by the training scripts. If the
    file is absent the honest answer is 'Not evaluated yet' -- never a number."""
    import json

    path = os.path.join(settings.MODEL_DIR, checkpoint_filename + ".metrics.json")
    if not os.path.isfile(path):
        return NOT_EVALUATED
    try:
        with open(path) as fh:
            data = json.load(fh)
        t = data.get("test", {})
        parts = [f"{k} {t[k]:.3f}" for k in ("accuracy", "f1", "roc_auc") if isinstance(t.get(k), (int, float))]
        return {
            "state": "SYNTHETIC_ONLY" if synthetic else "EVALUATED",
            "summary": ", ".join(parts) + (" (synthetic data only)" if synthetic else ""),
            "dataset": data.get("dataset"),
            "n": t.get("n"),
            "note": data.get("note"),
        }
    except (OSError, ValueError):
        return NOT_EVALUATED


@router.get("/models")
def model_status():
    deepfake_ckpt = os.path.isfile(os.path.join(settings.MODEL_DIR, "deepfake_effnet.pt"))
    risk_v2 = os.path.isfile(os.path.join(settings.MODEL_DIR, "risk_model_v2.joblib"))
    risk_ckpt = risk_v2 or os.path.isfile(os.path.join(settings.MODEL_DIR, "risk_model.joblib"))

    def _installed(module_name: str) -> bool:
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    has_easyocr = _installed("easyocr")
    has_insightface = _installed("insightface")
    has_mediapipe = _installed("mediapipe")
    has_torch = _installed("torch")
    has_scipy = _installed("scipy")

    models = [
        {
            "model": "Document OCR (EasyOCR)",
            "status": "Pre-trained, installed and available" if has_easyocr else "NOT INSTALLED in this environment -- pipeline is fully implemented, install easyocr+torch per requirements.txt to enable",
            "version": "easyocr-en",
            "purpose": "Extract text fields from identity documents",
            "device": "CPU",
        },
        {
            "model": "Document Tampering Baseline",
            "status": "Rule-based (ELA + noise + copy-move), not a trained classifier -- available (OpenCV only)",
            "version": "cv_heuristic_v1",
            "purpose": "Flag possible document tampering/forgery",
            "device": "CPU",
        },
        {
            "model": "Face Detection (MediaPipe)",
            "status": "Pre-trained, installed and available" if has_mediapipe else "NOT INSTALLED in this environment",
            "version": "mediapipe-face-detection",
            "purpose": "Locate faces in ID photo and live frames",
            "device": "CPU",
        },
        {
            "model": "Face Recognition (InsightFace / ArcFace)",
            "status": "Pre-trained, installed and available" if has_insightface else "NOT INSTALLED in this environment -- pipeline is fully implemented, install insightface+onnxruntime per requirements.txt to enable",
            "version": "buffalo_l",
            "purpose": "Generate face embeddings for identity matching",
            "device": "CPU",
        },
        {
            "model": "Liveness Detection",
            "status": (
                "Rule-based (EAR blink + head-turn displacement), available"
                if has_mediapipe
                else "Rule-based, but NOT INSTALLED in this environment (needs mediapipe)"
            ),
            "version": "landmark_heuristic_v1",
            "purpose": "Verify blink/head-turn challenge-response",
            "device": "CPU",
        },
        {
            "model": "rPPG (Remote Photoplethysmography)",
            "status": (
                "Rule-based signal processing (CHROM method), available"
                if (has_mediapipe and has_scipy)
                else f"NOT INSTALLED in this environment (needs {'mediapipe' if not has_mediapipe else ''}"
                     f"{' and ' if not has_mediapipe and not has_scipy else ''}{'scipy' if not has_scipy else ''})"
            ),
            "version": "chrom_v1",
            "purpose": "Physiological pulse signal as a supplementary liveness check -- one signal among several, not a standalone deepfake/spoof detector",
            "device": "CPU",
        },
        {
            "model": "Deepfake Detection (EfficientNet-B0)",
            "status": (
                ("Fine-tuned checkpoint loaded" if deepfake_ckpt else
                 "TRAINING REQUIRED -- no trained checkpoint (deepfake_effnet.pt); no probability is reported until one exists (see docs/training.md)")
                if has_torch else "NOT INSTALLED in this environment -- pipeline is fully implemented, install torch+torchvision per requirements.txt to enable"
            ),
            "version": "efficientnet_b0_finetuned_v1" if deepfake_ckpt else "efficientnet_b0_imagenet_untuned",
            "purpose": "Estimate probability that video frames are manipulated",
            "device": "CPU",
        },
        {
            "model": "Replay Attack Detection",
            "status": "Rule-based (moire/FFT + temporal consistency + loop periodicity), available (OpenCV only)",
            "version": "replay_heuristic_v1",
            "purpose": "Detect screen replay / pre-recorded video presentation",
            "device": "CPU",
        },
        {
            "model": "Fraud Risk Engine",
            "status": ("Trained on SYNTHETIC data (v2 incl. rPPG as a trained feature), available" if risk_v2 else "Trained on SYNTHETIC data (v1, 7 features), available") if risk_ckpt else "TRAINING REQUIRED -- falling back to a transparent weighted-rule baseline (not a trained model)",
            "version": ("xgboost_risk_v2_rppg_synthetic" if risk_v2 else "xgboost_risk_v1_synthetic") if risk_ckpt else "rule_based_fallback_untrained",
            "purpose": "Combine all upstream signals into a single 0-100 fraud risk score",
            "device": "CPU",
        },
    ]
    for m in models:
        name = m["model"]
        if name.startswith("Deepfake"):
            m["evaluation"] = _evaluation("deepfake_effnet.pt")
        elif name.startswith("Fraud Risk"):
            m["evaluation"] = _evaluation("risk_model_v2.joblib" if risk_v2 else "risk_model.joblib", synthetic=True)
        else:
            m["evaluation"] = NOT_EVALUATED
    return models


@router.get("/health")
def health():
    return {"status": "ok"}
