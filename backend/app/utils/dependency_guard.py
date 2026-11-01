"""
Wraps calls into ML modules whose heavy third-party dependency
(torch / easyocr / insightface / mediapipe) may not be installed in
the current environment. Converts an ImportError from a lazy `import
x` inside an `app.ml.*` function into a clean, honest HTTP 503 rather
than letting FastAPI return an opaque 500.

This is purely an environment-availability concern -- it never
fabricates a result. If the dependency IS installed, the real model
runs exactly as implemented in app/ml/*.py.
"""
from __future__ import annotations

import functools

from fastapi import HTTPException, status


def with_dependency_error_handling(component_name: str):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except ImportError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        f"{component_name} is unavailable: a required Python package "
                        f"is not installed in this environment ({exc}). Install the "
                        f"full backend/requirements.txt on a machine with sufficient "
                        f"disk/network to enable this module."
                    ),
                ) from exc

        return wrapper

    return decorator
