from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class RiskAssessmentOut(BaseModel):

    model_config = ConfigDict(protected_namespaces=())
    fraud_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    decision: Optional[str] = None
    feature_contributions: Optional[Dict[str, Any]] = None
    explanation_text: Optional[str] = None
    model_version: Optional[str] = None
