"""
Application entrypoint.

Run with:
    uvicorn app.main:app --reload

On startup this:
  1. Configures logging.
  2. Ensures upload/temp/model storage directories exist.
  3. Creates database tables if they don't exist (for local/dev use;
     a real deployment should use versioned migrations instead).
  4. Registers all API routers.

It deliberately does NOT eagerly force-load every heavyweight ML
model (EasyOCR/InsightFace/MediaPipe/EfficientNet) at import time --
each `app/ml/*.py` module lazy-loads and caches its own model on
first use (see their `@lru_cache`-decorated loaders). This keeps
`uvicorn app.main:app --reload` fast to boot and lets the app run
even when a given optional dependency isn't installed, surfacing a
clear per-request error instead of crashing the whole server.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, kyc, reviewer, system
from app.core.config import settings
from app.core.database import Base, engine
from app.utils.logging_config import configure_logging, logger
from app.utils.temp_file_manager import ensure_dirs, purge_temp_videos

# Import models so they're registered on Base.metadata before create_all
from app.models import document, kyc_case, results, user  # noqa: F401

configure_logging()

app = FastAPI(
    title="Deepfake-Resistant Video KYC Verification System",
    description=(
        "Academic prototype combining document verification, biometric "
        "matching, liveness detection, deepfake detection, replay-attack "
        "detection and explainable fraud-risk scoring into a single "
        "Video KYC workflow. Not connected to any real Aadhaar/PAN/bank "
        "database."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.on_event("startup")
def on_startup():
    ensure_dirs()
    purge_temp_videos()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured. Storage directories ready.")
    if any(w in settings.JWT_SECRET_KEY.lower() for w in ("change", "dev-")):
        logger.warning("JWT_SECRET_KEY is a placeholder/dev value -- set a long random secret in .env before any real deployment.")


@app.get("/")
def root():
    return {
        "service": "Deepfake-Resistant Video KYC Verification System",
        "status": "running",
        "docs": "/docs",
        "note": "Academic prototype. No real government/bank database integration.",
    }


app.include_router(auth.router)
app.include_router(kyc.router)
app.include_router(reviewer.router)
app.include_router(system.router)
app.include_router(admin.router)
