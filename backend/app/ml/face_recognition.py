"""
Model B — Face detection (MediaPipe) and Model C — Face recognition
(InsightFace / ArcFace embeddings).

Both are used as pre-trained, off-the-shelf models — training a face
recognition network from scratch is out of scope for this project and
would need far more data/compute than a student prototype can access.
The prototype's contribution is in how these signals are combined with
document, liveness, deepfake and replay checks downstream, not in the
face-recognition model itself.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_mediapipe_face_detector():
    import mediapipe as mp

    return mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)


@lru_cache(maxsize=1)
def _get_mediapipe_face_mesh():
    import mediapipe as mp

    return mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )


@lru_cache(maxsize=1)
def _get_insightface_app():
    """
    Loads the InsightFace 'buffalo_l' pack (detector + ArcFace recognition).
    NOTE: on first run this downloads pretrained weights from InsightFace's
    model zoo. If the deployment environment has no internet access, this
    call will raise — see README "Model Setup" for offline instructions.
    """
    import insightface

    app = insightface.app.FaceAnalysis(name="buffalo_l")
    app.prepare(ctx_id=-1, det_size=(640, 640))  # ctx_id=-1 => CPU
    return app


def detect_faces_mediapipe(image_bgr: np.ndarray) -> List[Dict[str, Any]]:
    detector = _get_mediapipe_face_detector()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = detector.process(rgb)
    faces = []
    h, w = image_bgr.shape[:2]
    if result.detections:
        for det in result.detections:
            box = det.location_data.relative_bounding_box
            faces.append(
                {
                    "bbox": {
                        "x": max(0, int(box.xmin * w)),
                        "y": max(0, int(box.ymin * h)),
                        "w": int(box.width * w),
                        "h": int(box.height * h),
                    },
                    "confidence": float(det.score[0]) if det.score else None,
                }
            )
    return faces


def assess_face_quality(image_bgr: np.ndarray, bbox: Dict[str, int]) -> float:
    """Simple, explainable quality heuristic: sharpness (Laplacian variance) + brightness + size."""
    x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
    crop = image_bgr[y : y + h, x : x + w]
    if crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_score = np.clip(sharpness / 300.0, 0, 1)
    brightness = gray.mean() / 255.0
    brightness_score = 1.0 - abs(brightness - 0.5) * 2  # best at mid brightness
    size_score = np.clip((w * h) / (150 * 150), 0, 1)
    quality = float(np.clip(0.5 * sharpness_score + 0.25 * brightness_score + 0.25 * size_score, 0, 1))
    return round(quality, 4)


def get_face_embedding(image_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Returns a single 512-d ArcFace embedding for the largest detected face, or None."""
    app = _get_insightface_app()
    faces = app.get(image_bgr)
    if not faces:
        return None
    # pick the largest face by bbox area (most likely the primary subject)
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return faces[0].normed_embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-8
    return float(np.dot(a, b) / denom)


def compare_faces(live_image_bgr: np.ndarray, id_image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Full face-matching pipeline: detect + quality-check + embed + compare.
    threshold is read from settings so it's configurable, not hard-coded logic.
    """
    live_faces = detect_faces_mediapipe(live_image_bgr)
    id_faces = detect_faces_mediapipe(id_image_bgr)

    if not live_faces:
        return {"error": "NO_FACE_DETECTED_LIVE"}
    if not id_faces:
        return {"error": "NO_FACE_DETECTED_ID"}

    multiple_faces = len(live_faces) > 1
    quality = assess_face_quality(live_image_bgr, live_faces[0]["bbox"])

    live_embedding = get_face_embedding(live_image_bgr)
    id_embedding = get_face_embedding(id_image_bgr)

    if live_embedding is None or id_embedding is None:
        return {"error": "EMBEDDING_FAILED"}

    similarity = cosine_similarity(live_embedding, id_embedding)
    # InsightFace cosine similarity is roughly in [-1, 1]; clip to [0, 1] for score display
    similarity_display = float(np.clip((similarity + 1) / 2, 0, 1))

    threshold = settings.FACE_MATCH_THRESHOLD
    match_status = "MATCHED" if similarity_display >= threshold else "NOT_MATCHED"

    return {
        "similarity_score": round(similarity_display, 4),
        "match_status": match_status,
        "face_quality_score": quality,
        "multiple_faces_detected": multiple_faces,
        "threshold_used": threshold,
    }
