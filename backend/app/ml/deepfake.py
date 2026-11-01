"""
Model E — Deepfake detection.

STATUS: reports TRAINING_REQUIRED (no probability) until
MODEL_DIR/deepfake_effnet.pt exists -- produce it with
ml/training/train_deepfake_model.py (see docs/training.md).

Baseline architecture: EfficientNet-B0 (torchvision), binary head
(real=0 / fake=1), fine-tuned on a subset of FaceForensics++/Celeb-DF.

IMPORTANT — model status:
This module loads fine-tuned weights from `MODEL_DIR/deepfake_effnet.pt`
if present. Training that checkpoint requires a GPU and a downloaded
dataset (see ml/training/train_deepfake_model.py) which this environment
does not have. Until that checkpoint exists, `load_model()` falls back
to ImageNet-pretrained EfficientNet-B0 weights and the module reports
`model_version = "efficientnet_b0_imagenet_untuned"` with every
response — the UI must surface this so nobody mistakes an untrained
baseline for a validated deepfake detector. This satisfies the "never
fake AI results" requirement: the probability returned is a genuine
forward pass through a real network, just one whose fake/real head has
not yet been trained on deepfake data.

Frame aggregation: rather than trusting a single frame, we sample
`DEEPFAKE_FRAME_SAMPLE_RATE`-th frames up to `DEEPFAKE_MAX_FRAMES`,
run each through the classifier, and report the mean probability, the
count of frames analyzed, and which frame indices scored above 0.5
("suspicious frames") for the reviewer to inspect.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings

MODEL_VERSION_TUNED = "efficientnet_b0_finetuned_v1"
MODEL_VERSION_UNTUNED = "efficientnet_b0_imagenet_untuned"


@lru_cache(maxsize=1)
def _load_model():
    import torch
    import torch.nn as nn
    from torchvision.models import efficientnet_b0

    model = efficientnet_b0(weights="IMAGENET1K_V1")
    # Replace classifier head with a binary real/fake head
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, 2)

    checkpoint_path = os.path.join(settings.MODEL_DIR, "deepfake_effnet.pt")
    version = MODEL_VERSION_UNTUNED
    if os.path.isfile(checkpoint_path):
        state_dict = torch.load(checkpoint_path, map_location="cpu")
        model.load_state_dict(state_dict)
        version = MODEL_VERSION_TUNED
    else:
        # No fine-tuned checkpoint: head is randomly initialized.
        # We still run it (per "no faked outputs" — this is a real,
        # documented forward pass) but the version string makes the
        # untrained status explicit everywhere it's surfaced.
        pass

    model.eval()
    return model, version


FACE_CROP_MARGIN = 0.25  # context around the detected face box (fraction of box size)


def crop_face(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """
    Crops the largest detected face (with margin). Returns None if no face
    is found. This SAME function is used by inference and by
    ml/training/prepare_deepfake_dataset.py, so the classifier sees
    identically-prepared inputs at training and prediction time -- a
    train/serve mismatch here would silently ruin accuracy.
    """
    from app.ml.face_recognition import detect_faces_mediapipe

    faces = detect_faces_mediapipe(frame_bgr)
    if not faces:
        return None
    b = max(faces, key=lambda f: f["bbox"]["w"] * f["bbox"]["h"])["bbox"]
    h_img, w_img = frame_bgr.shape[:2]
    mx, my = int(b["w"] * FACE_CROP_MARGIN), int(b["h"] * FACE_CROP_MARGIN)
    x1, y1 = max(0, b["x"] - mx), max(0, b["y"] - my)
    x2, y2 = min(w_img, b["x"] + b["w"] + mx), min(h_img, b["y"] + b["h"] + my)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame_bgr[y1:y2, x1:x2]


def preprocess_frame(frame_bgr: np.ndarray) -> "torch.Tensor":  # noqa: F821
    import torch

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224))
    tensor = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    tensor = (tensor - mean) / std
    return tensor.unsqueeze(0)


def predict_frame(model, frame_bgr: np.ndarray) -> float:
    import torch

    with torch.no_grad():
        tensor = preprocess_frame(frame_bgr)
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        fake_prob = float(probs[0, 1].item())
    return fake_prob


def sample_frames(frames: List[np.ndarray]) -> List[Tuple[int, np.ndarray]]:
    step = max(1, settings.DEEPFAKE_FRAME_SAMPLE_RATE)
    sampled = [(i, f) for i, f in enumerate(frames) if i % step == 0]
    return sampled[: settings.DEEPFAKE_MAX_FRAMES]


def aggregate_predictions(frame_scores: List[Tuple[int, float]]) -> Dict[str, Any]:
    if not frame_scores:
        return {"deepfake_probability": None, "status": "NO_FRAMES", "frames_analyzed": 0, "suspicious_frame_indices": []}

    probs = [s for _, s in frame_scores]
    mean_prob = float(np.mean(probs))
    suspicious = [idx for idx, s in frame_scores if s >= 0.5]

    if mean_prob < 0.3:
        status = "LOW_SUSPICION"
    elif mean_prob < 0.7:
        status = "MEDIUM_SUSPICION"
    else:
        status = "HIGH_SUSPICION"

    return {
        "deepfake_probability": round(mean_prob, 4),
        "status": status,
        "frames_analyzed": len(frame_scores),
        "suspicious_frame_indices": suspicious,
    }


def checkpoint_path() -> str:
    return os.path.join(settings.MODEL_DIR, "deepfake_effnet.pt")


def analyze_video_frames(frames: List[np.ndarray]) -> Dict[str, Any]:
    """Full pipeline: sample frames -> predict each -> aggregate.

    If no fine-tuned checkpoint exists, NO inference is run and NO
    probability is reported: a randomly initialized classification head
    produces arbitrary numbers that would look like a real finding (and
    would feed the risk model). The honest result is TRAINING_REQUIRED
    with probability None; callers treat the signal as unavailable.
    """
    if not os.path.isfile(checkpoint_path()):
        return {
            "deepfake_probability": None,
            "status": "TRAINING_REQUIRED",
            "frames_analyzed": 0,
            "suspicious_frame_indices": [],
            "model_version": MODEL_VERSION_UNTUNED,
        }
    model, version = _load_model()
    sampled = sample_frames(frames)
    frame_scores = []
    for idx, f in sampled:
        face = crop_face(f)
        if face is None:
            continue  # no face in this frame: nothing meaningful to classify
        frame_scores.append((idx, predict_frame(model, face)))
    if not frame_scores:
        return {
            "deepfake_probability": None, "status": "NO_FACE_FRAMES", "frames_analyzed": 0,
            "suspicious_frame_indices": [], "model_version": version,
        }
    result = aggregate_predictions(frame_scores)
    result["model_version"] = version
    return result


def generate_gradcam(frame_bgr: np.ndarray, output_path: Optional[str] = None) -> Optional[str]:
    """
    Generates a Grad-CAM overlay for the most suspicious frame, highlighting
    which image regions most influenced the deepfake classifier's decision.
    Returns the saved overlay path, or None if generation fails.
    """
    try:
        import torch
        import torch.nn.functional as F

        model, _ = _load_model()
        target_layer = model.features[-1]

        activations = {}
        gradients = {}

        def fwd_hook(module, inp, out):
            activations["value"] = out.detach()

        def bwd_hook(module, grad_in, grad_out):
            gradients["value"] = grad_out[0].detach()

        h1 = target_layer.register_forward_hook(fwd_hook)
        h2 = target_layer.register_full_backward_hook(bwd_hook)

        tensor = preprocess_frame(frame_bgr)
        tensor.requires_grad_(True)
        logits = model(tensor)
        fake_class_score = logits[0, 1]
        model.zero_grad()
        fake_class_score.backward()

        h1.remove()
        h2.remove()

        acts = activations["value"][0]     # C,H,W
        grads = gradients["value"][0]      # C,H,W
        weights = grads.mean(dim=(1, 2))   # C
        cam = torch.relu((weights[:, None, None] * acts).sum(0))
        cam = cam / (cam.max() + 1e-8)
        cam_np = cam.cpu().numpy()
        cam_resized = cv2.resize(cam_np, (frame_bgr.shape[1], frame_bgr.shape[0]))
        heatmap = cv2.applyColorMap((cam_resized * 255).astype(np.uint8), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(frame_bgr, 0.6, heatmap, 0.4, 0)

        if output_path:
            cv2.imwrite(output_path, overlay)
            return output_path
        return None
    except Exception:
        # Grad-CAM is a supplementary explainability feature; if it fails
        # (e.g. incompatible torch build) we degrade gracefully rather than
        # breaking the KYC pipeline.
        return None
