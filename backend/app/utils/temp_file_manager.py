"""
Temporary-file lifecycle helpers.

RAW KYC VIDEOS AND DOCUMENT IMAGES ARE NEVER PERSISTED PERMANENTLY.
Everything written here lives under settings.TEMP_VIDEO_DIR /
settings.UPLOAD_DIR and is deleted once the corresponding pipeline
stage finishes reading it. Only structured metadata/results
(scores, statuses, extracted text) are written to PostgreSQL.
"""
import os
import shutil
import uuid

from app.core.config import settings
from app.utils.logging_config import logger


def ensure_dirs() -> None:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_VIDEO_DIR, exist_ok=True)
    os.makedirs(settings.MODEL_DIR, exist_ok=True)


def save_temp_bytes(raw_bytes: bytes, directory: str, suffix: str) -> str:
    ensure_dirs()
    filename = f"{uuid.uuid4().hex}{suffix}"
    path = os.path.join(directory, filename)
    with open(path, "wb") as f:
        f.write(raw_bytes)
    return path


def delete_path(path: str, attempts: int = 5, delay: float = 0.25) -> bool:
    """
    Deletes a temporary file/dir. Returns True if it is gone.

    Retries a few times because on Windows a file can stay locked for a
    moment after a video reader releases it. If deletion STILL fails, this
    logs at ERROR level (the privacy guarantee "raw video is deleted" has
    then been violated and must be visible) instead of failing silently;
    the startup purge below removes any such leftover on the next launch.
    """
    import time

    if not path:
        return True
    for attempt in range(1, attempts + 1):
        try:
            if os.path.isfile(path):
                os.remove(path)
                logger.info(f"Deleted temporary file: {path}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Deleted temporary directory: {path}")
            return True
        except OSError as e:
            if attempt == attempts:
                logger.error(f"PRIVACY WARNING: could not delete temporary file {path} after {attempts} attempts: {e}")
                return False
            time.sleep(delay)
    return False


def purge_temp_videos() -> int:
    """Removes any leftover raw videos in TEMP_VIDEO_DIR (e.g. after a crash). Run at startup."""
    removed = 0
    d = settings.TEMP_VIDEO_DIR
    if not os.path.isdir(d):
        return 0
    for name in os.listdir(d):
        if name.startswith("."):
            continue
        if delete_path(os.path.join(d, name)):
            removed += 1
    if removed:
        logger.warning(f"Startup purge removed {removed} leftover temporary video file(s).")
    return removed
