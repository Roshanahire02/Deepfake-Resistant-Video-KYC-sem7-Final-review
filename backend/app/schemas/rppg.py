from typing import Optional

from pydantic import BaseModel


class RPPGResultOut(BaseModel):
    status: Optional[str] = None  # AVAILABLE | INSUFFICIENT_SIGNAL | UNAVAILABLE | ERROR
    heart_rate_bpm: Optional[float] = None
    signal_quality: Optional[float] = None
    periodicity_score: Optional[float] = None
    temporal_consistency: Optional[float] = None
    rppg_score: Optional[float] = None
    usable_frames: Optional[int] = None
    usable_frame_ratio: Optional[float] = None
    roi_stability: Optional[float] = None
    method_version: Optional[str] = None
    message: Optional[str] = None
