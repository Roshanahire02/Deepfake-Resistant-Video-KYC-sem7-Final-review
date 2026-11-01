from typing import Optional

from pydantic import BaseModel


class LivenessChallengeRequest(BaseModel):
    challenge_type: str  # BLINK_TWICE | TURN_LEFT | TURN_RIGHT


class LivenessResultOut(BaseModel):
    challenge_type: Optional[str] = None
    passed: Optional[bool] = None
    motion_score: Optional[float] = None
    blink_count: Optional[int] = None
    confidence: Optional[float] = None
