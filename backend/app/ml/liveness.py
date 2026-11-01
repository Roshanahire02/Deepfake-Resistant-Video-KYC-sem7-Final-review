"""
Model D — Liveness detection via challenge-response.

Uses MediaPipe Face Mesh landmarks across a sequence of frames to
verify the requested challenge actually happened:

- BLINK_TWICE: tracks the Eye Aspect Ratio (EAR) over time and counts
  dips below a threshold as blinks.
- TURN_LEFT / TURN_RIGHT: tracks horizontal nose-tip displacement
  relative to the initial frame to confirm real head rotation (as
  opposed to a static photo, which cannot move).

This is a transparent, rule-based approach rather than a trained
black-box classifier, which keeps it explainable and avoids needing a
dedicated anti-spoofing dataset — a legitimate design choice for an
academic prototype, and it is documented as such (see README
"Limitations": determined attackers with video replays of a genuine
person performing the challenge are NOT caught by this layer alone —
that is what the deepfake and replay modules are for).
"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from app.core.config import settings
from app.ml.face_recognition import _get_mediapipe_face_mesh

# MediaPipe Face Mesh landmark indices for eyes (subset used for EAR)
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
NOSE_TIP = 1


def _eye_aspect_ratio(landmarks, eye_indices, w, h) -> float:
    pts = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in eye_indices])
    # vertical distances
    a = np.linalg.norm(pts[1] - pts[5])
    b = np.linalg.norm(pts[2] - pts[4])
    # horizontal distance
    c = np.linalg.norm(pts[0] - pts[3])
    if c == 0:
        return 0.0
    return float((a + b) / (2.0 * c))


def _extract_landmarks_per_frame(frames: List[np.ndarray]) -> List[Dict[str, Any]]:
    mesh = _get_mediapipe_face_mesh()
    per_frame = []
    for frame in frames:
        h, w = frame.shape[:2]
        rgb = frame[:, :, ::-1]
        result = mesh.process(rgb)
        if not result.multi_face_landmarks:
            per_frame.append(None)
            continue
        landmarks = result.multi_face_landmarks[0].landmark
        left_ear = _eye_aspect_ratio(landmarks, LEFT_EYE, w, h)
        right_ear = _eye_aspect_ratio(landmarks, RIGHT_EYE, w, h)
        nose_x = landmarks[NOSE_TIP].x * w
        per_frame.append({"ear": (left_ear + right_ear) / 2.0, "nose_x": nose_x, "frame_w": w})
    return per_frame


def _analyze_blink(frames_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    ears = [f["ear"] for f in frames_data if f is not None]
    if len(ears) < 3:
        return {"passed": False, "blink_count": 0, "motion_score": 0.0, "confidence": 0.0}

    threshold = settings.LIVENESS_EAR_BLINK_THRESHOLD
    below = np.array(ears) < threshold
    # count rising edges out of "closed" state as blinks
    blink_count = int(np.sum((below[:-1] == True) & (below[1:] == False)))  # noqa: E712
    motion_score = float(np.std(ears))
    passed = blink_count >= 2
    confidence = float(np.clip(motion_score * 10, 0, 1))
    return {"passed": passed, "blink_count": blink_count, "motion_score": round(motion_score, 4), "confidence": round(confidence, 4)}


def _analyze_head_turn(frames_data: List[Dict[str, Any]], direction: str) -> Dict[str, Any]:
    valid = [f for f in frames_data if f is not None]
    if len(valid) < 3:
        return {"passed": False, "motion_score": 0.0, "confidence": 0.0}

    nose_positions = np.array([f["nose_x"] / f["frame_w"] for f in valid])  # normalized 0-1
    start, end = nose_positions[0], nose_positions[-1]
    displacement = end - start  # positive = moved right in frame

    # NOTE: "left"/"right" here refer to the user's own left/right, which is
    # mirrored in a front-facing camera view (frame right = user's left).
    required_sign = 1 if direction == "TURN_LEFT" else -1
    moved_enough = abs(displacement) > 0.05
    correct_direction = np.sign(displacement) == required_sign or displacement == 0

    passed = bool(moved_enough and correct_direction)
    motion_score = float(abs(displacement))
    confidence = float(np.clip(motion_score * 8, 0, 1))
    return {"passed": passed, "motion_score": round(motion_score, 4), "confidence": round(confidence, 4)}


def analyze_liveness(frames: List[np.ndarray], challenge_type: str) -> Dict[str, Any]:
    """
    frames: ordered list of BGR frames captured during the challenge window.
    challenge_type: one of BLINK_TWICE | TURN_LEFT | TURN_RIGHT
    """
    frames_data = _extract_landmarks_per_frame(frames)
    detected_frames = sum(1 for f in frames_data if f is not None)

    if detected_frames < max(3, len(frames) // 3):
        return {
            "challenge_type": challenge_type,
            "passed": False,
            "motion_score": 0.0,
            "blink_count": 0,
            "confidence": 0.0,
            "error": "INSUFFICIENT_FACE_DETECTION",
        }

    if challenge_type == "BLINK_TWICE":
        result = _analyze_blink(frames_data)
        result["blink_count"] = result.get("blink_count", 0)
    elif challenge_type in ("TURN_LEFT", "TURN_RIGHT"):
        result = _analyze_head_turn(frames_data, challenge_type)
        result["blink_count"] = None
    else:
        return {"challenge_type": challenge_type, "passed": False, "error": "UNKNOWN_CHALLENGE_TYPE"}

    result["challenge_type"] = challenge_type
    return result
