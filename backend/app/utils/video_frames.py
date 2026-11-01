"""Decode an uploaded video clip into BGR frames (+ a trustworthy fps) for the ML pipeline."""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import cv2
import numpy as np
from fastapi import HTTPException

MIN_PLAUSIBLE_FPS = 5.0
MAX_PLAUSIBLE_FPS = 120.0


def estimate_fps(timestamps_ms: Sequence[float], reported_fps: Optional[float]) -> float:
    """
    Best available frame rate, or 0.0 if it can't be trusted (callers then use
    the configured fallback, never a garbage value).

    Browser MediaRecorder WebM files usually carry no proper fps header, so
    OpenCV may report 0, 1000 or 90000. A wrong fps silently corrupts the
    rPPG heart-rate conversion, so we (1) MEASURE fps from the decoded frame
    timestamps when they are sane, (2) else accept the container's value only
    if it is plausible, (3) else report unknown.
    """
    ts = list(timestamps_ms)
    if len(ts) >= 10:
        span = ts[-1] - ts[0]
        if span > 0 and all(b >= a for a, b in zip(ts, ts[1:])):
            measured = (len(ts) - 1) / (span / 1000.0)
            if MIN_PLAUSIBLE_FPS <= measured <= MAX_PLAUSIBLE_FPS:
                return float(measured)
    if reported_fps and MIN_PLAUSIBLE_FPS <= reported_fps <= MAX_PLAUSIBLE_FPS:
        return float(reported_fps)
    return 0.0


def extract_frames(video_path: str, max_frames: int = 150) -> Tuple[List[np.ndarray], float]:
    """Returns (frames, fps). fps == 0.0 means "unknown" (see estimate_fps)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Could not open uploaded video file.")
    frames: List[np.ndarray] = []
    timestamps: List[float] = []
    try:
        reported = cap.get(cv2.CAP_PROP_FPS) or 0.0
        while len(frames) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(frame)
            timestamps.append(cap.get(cv2.CAP_PROP_POS_MSEC))
    finally:
        cap.release()
    if not frames:
        raise HTTPException(status_code=400, detail="No frames could be decoded from the uploaded video.")
    return frames, estimate_fps(timestamps, reported)
