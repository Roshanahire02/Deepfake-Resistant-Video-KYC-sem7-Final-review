"""
Small in-memory sliding-window rate limiter used on /auth/login and
/auth/register to slow brute-force and mass-signup attempts.

Per-process memory is adequate for this single-server prototype; behind
multiple workers/instances the counters would move to Redis (documented
in the README's production notes). Limits are configurable in settings.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def reset() -> None:
    with _lock:
        _hits.clear()


def limit(bucket: str, per_minute_attr: str):
    """FastAPI dependency factory: limit(bucket, 'RATE_LIMIT_LOGIN_PER_MIN')."""

    def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        max_hits = getattr(settings, per_minute_attr)
        client = request.client.host if request.client else "unknown"
        key = f"{bucket}:{client}"
        now = time.monotonic()
        with _lock:
            q = _hits[key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= max_hits:
                retry = max(1, int(60 - (now - q[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many attempts. Please wait {retry}s and try again.",
                    headers={"Retry-After": str(retry)},
                )
            q.append(now)

    return dependency
