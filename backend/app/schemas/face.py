from typing import Optional

from pydantic import BaseModel


class FaceVerificationOut(BaseModel):
    similarity_score: Optional[float] = None
    match_status: Optional[str] = None
    face_quality_score: Optional[float] = None
    multiple_faces_detected: bool = False
    threshold_used: Optional[float] = None
