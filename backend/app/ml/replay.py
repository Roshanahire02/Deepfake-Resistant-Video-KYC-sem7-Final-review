"""
Replay attack detection.

Detects signals consistent with a video being replayed off a second
screen or a pre-recorded clip being shown to the camera, using:

1. Moire/screen-pattern detection: a high-frequency FFT energy check —
   phone/monitor screens photographed by another camera often produce
   periodic moire artifacts not present in a genuine live face.
2. Temporal micro-motion consistency: genuine live video has small,
   irregular motion (breathing, micro head movement); a replayed video
   captured off a screen often shows either unnaturally smooth motion
   (video-of-video re-encoding) or a static/frozen frame pattern.
3. Frame-difference periodicity: looks for repeating frame-difference
   patterns that can indicate a looped/short pre-recorded clip.

Like the liveness module, this is a transparent, rule-based baseline
appropriate for an academic prototype rather than a trained
presentation-attack-detection network (which would need a dedicated
PAD dataset with licensing the project scope doesn't call for).
"""
from __future__ import annotations

from typing import Any, Dict, List

import cv2
import numpy as np


def _moire_score(frame_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.log(np.abs(fshift) + 1)
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    # exclude low-frequency center (DC/global structure), look at mid-to-high frequency ring
    mask = np.ones((h, w), dtype=bool)
    radius_inner, radius_outer = min(h, w) // 8, min(h, w) // 2
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    ring = (dist > radius_inner) & (dist < radius_outer)
    ring_energy = magnitude[ring].mean() if ring.any() else 0.0
    total_energy = magnitude.mean() + 1e-6
    ratio = float(ring_energy / total_energy)
    return float(np.clip((ratio - 0.9) * 3.0, 0.0, 1.0))


def _temporal_consistency_score(frames: List[np.ndarray]) -> float:
    if len(frames) < 3:
        return 0.0
    diffs = []
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    for i in range(1, len(grays)):
        d = cv2.absdiff(grays[i], grays[i - 1])
        diffs.append(float(d.mean()))
    diffs = np.array(diffs)
    if diffs.mean() < 1e-3:
        # frames are essentially frozen — highly suspicious for a "live" feed
        return 1.0
    # unnaturally low variance in motion also suggests a re-encoded/looped clip
    variance_of_motion = float(diffs.std())
    score = float(np.clip(1.0 - variance_of_motion / 5.0, 0.0, 1.0)) if diffs.mean() < 2.0 else 0.0
    return score


def _loop_periodicity_score(frames: List[np.ndarray]) -> float:
    if len(frames) < 6:
        return 0.0
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    diffs = [float(cv2.absdiff(grays[i], grays[i - 1]).mean()) for i in range(1, len(grays))]
    arr = np.array(diffs)
    if arr.std() < 1e-6:
        return 0.0
    normalized = (arr - arr.mean()) / arr.std()
    autocorr = np.correlate(normalized, normalized, mode="full")
    autocorr = autocorr[len(autocorr) // 2 :]
    if len(autocorr) < 4:
        return 0.0
    peak = float(np.max(autocorr[2:]) / autocorr[0]) if autocorr[0] != 0 else 0.0
    return float(np.clip(peak, 0.0, 1.0))


def analyze_replay(frames: List[np.ndarray]) -> Dict[str, Any]:
    if not frames:
        return {"replay_probability": None, "status": "NO_FRAMES", "signals": {}}

    moire_scores = [_moire_score(f) for f in frames[:: max(1, len(frames) // 10)]]
    moire = float(np.mean(moire_scores)) if moire_scores else 0.0
    temporal = _temporal_consistency_score(frames)
    periodicity = _loop_periodicity_score(frames)

    weights = {"moire": 0.4, "temporal": 0.35, "periodicity": 0.25}
    replay_probability = weights["moire"] * moire + weights["temporal"] * temporal + weights["periodicity"] * periodicity
    replay_probability = float(np.clip(replay_probability, 0.0, 1.0))

    if replay_probability < 0.3:
        status = "NOT_DETECTED"
    elif replay_probability < 0.6:
        status = "SUSPECTED"
    else:
        status = "DETECTED"

    return {
        "replay_probability": round(replay_probability, 4),
        "status": status,
        "signals": {
            "moire_pattern_score": round(moire, 4),
            "temporal_consistency_score": round(temporal, 4),
            "loop_periodicity_score": round(periodicity, 4),
        },
    }
