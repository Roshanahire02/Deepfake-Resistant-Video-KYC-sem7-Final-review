"""
Central application configuration.

All secrets and environment-specific values are read from environment
variables (via a local .env file, see .env.example). Nothing here is
hard-coded, and risk thresholds are configurable rather than fixed
constants baked into the pipeline logic.
"""
import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ -- the anchor for .env and every relative path below, so the app
# behaves identically no matter which folder it is launched from.
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # Database. Default is SQLite (zero setup). PostgreSQL is optional and
    # has not been run end-to-end in this project.
    DATABASE_URL: str = "sqlite:///./storage/dev.db"

    # Auth
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Storage
    UPLOAD_DIR: str = "./storage/uploads"
    TEMP_VIDEO_DIR: str = "./storage/temp_video"
    MODEL_DIR: str = "./storage/models"
    MAX_UPLOAD_MB: int = 10

    # Risk engine thresholds - configurable, read at runtime
    RISK_LOW_MAX: int = 30
    RISK_MEDIUM_MAX: int = 70
    FACE_MATCH_THRESHOLD: float = 0.55

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # ML behaviour
    DEEPFAKE_FRAME_SAMPLE_RATE: int = 5  # analyze every Nth frame
    DEEPFAKE_MAX_FRAMES: int = 30
    LIVENESS_EAR_BLINK_THRESHOLD: float = 0.21  # eye-aspect-ratio threshold for a blink

    # Brute-force protection on auth endpoints (per client IP, sliding window)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MIN: int = 10
    RATE_LIMIT_REGISTER_PER_MIN: int = 5

    # rPPG (remote photoplethysmography) -- physiological liveness signal.
    # All thresholds configurable rather than scattered as magic numbers.
    RPPG_MIN_FRAMES: int = 40                 # below this, too short a clip to trust any estimate
    RPPG_MIN_FACE_DETECTION_RATIO: float = 0.6  # fraction of frames that must have a usable forehead ROI
    RPPG_MIN_SIGNAL_QUALITY: float = 0.35     # below this, report INSUFFICIENT_SIGNAL rather than a number
    RPPG_MIN_BPM: float = 40.0                # physiological heart-rate search band (resting-to-elevated)
    RPPG_MAX_BPM: float = 180.0
    RPPG_DEFAULT_FPS_FALLBACK: float = 15.0   # used only if the container/codec doesn't report a valid fps
    RPPG_METHOD: str = "CHROM"

    @model_validator(mode="after")
    def _anchor_relative_paths(self):
        """Resolve ./relative storage paths and a relative SQLite file against backend/."""
        for name in ("UPLOAD_DIR", "TEMP_VIDEO_DIR", "MODEL_DIR"):
            value = getattr(self, name)
            if not os.path.isabs(value):
                setattr(self, name, str((BACKEND_DIR / value).resolve()))
        prefix = "sqlite:///"
        if self.DATABASE_URL.startswith(prefix) and not self.DATABASE_URL.startswith("sqlite:////") and ":memory:" not in self.DATABASE_URL:
            rel = self.DATABASE_URL[len(prefix):]
            if not os.path.isabs(rel) and not (len(rel) > 1 and rel[1] == ":"):  # not "C:/..." either
                self.DATABASE_URL = prefix + (BACKEND_DIR / rel).resolve().as_posix()
        return self


settings = Settings()
