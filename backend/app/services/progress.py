"""
In-memory, per-case record of which pipeline stage is actually running.

The video endpoint blocks until analysis finishes, so the UI polls
GET /api/kyc/{case_id}/progress while that request is in flight. Stage
names are set by kyc_pipeline_service at the moment each stage really
starts -- nothing here is estimated or timed. Holds only a stage name
and timestamps (no biometric data). Per-process memory is fine for this
single-server prototype; a multi-worker deployment would move this to
Redis or a DB column.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Optional

STAGES = ["EXTRACTING_FRAMES", "LIVENESS", "DEEPFAKE", "REPLAY", "RPPG", "FACE_MATCH", "RISK"]

_lock = threading.Lock()
_state: Dict[str, dict] = {}


def start(case_id) -> None:
    with _lock:
        _state[str(case_id)] = {"stage": STAGES[0], "completed": [], "state": "RUNNING", "updated_at": time.time()}


def set_stage(case_id, stage: str) -> None:
    with _lock:
        st = _state.setdefault(str(case_id), {"stage": stage, "completed": [], "state": "RUNNING", "updated_at": time.time()})
        if st["stage"] != stage and st["stage"] not in st["completed"]:
            st["completed"].append(st["stage"])
        st["stage"] = stage
        st["state"] = "RUNNING"
        st["updated_at"] = time.time()


def finish(case_id, ok: bool = True) -> None:
    with _lock:
        st = _state.setdefault(str(case_id), {"stage": None, "completed": [], "state": "DONE", "updated_at": time.time()})
        if st["stage"] and st["stage"] not in st["completed"] and ok:
            st["completed"].append(st["stage"])
        st["state"] = "DONE" if ok else "ERROR"
        st["updated_at"] = time.time()


def get(case_id) -> Optional[dict]:
    with _lock:
        st = _state.get(str(case_id))
        return dict(st, completed=list(st["completed"])) if st else None
