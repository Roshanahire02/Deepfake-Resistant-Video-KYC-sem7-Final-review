from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class ReviewerDecisionIn(BaseModel):
    action: str  # APPROVE | REJECT | MANUAL_REVIEW
    notes: Optional[str] = None


class ReviewerCaseListItem(BaseModel):
    case_id: str
    user_email: str
    status: str
    risk_level: Optional[str] = None
    fraud_risk_score: Optional[float] = None
    created_at: datetime


class ReviewerCaseDetail(BaseModel):
    case: Dict[str, Any]
    document: Optional[Dict[str, Any]] = None
    face: Optional[Dict[str, Any]] = None
    liveness: Optional[Dict[str, Any]] = None
    deepfake: Optional[Dict[str, Any]] = None
    replay: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
