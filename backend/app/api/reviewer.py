from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.document import OCRResult
from app.models.kyc_case import KYCCase
from app.models.results import (
    DeepfakeResult,
    FaceVerification,
    LivenessResult,
    ReplayResult,
    RPPGResult,
    ReviewerAction,
    ReviewerActionType,
    RiskAssessment,
)
from app.models.user import User, UserRole
from app.schemas.reviewer import ReviewerDecisionIn

router = APIRouter(prefix="/api/reviewer", tags=["reviewer"])

reviewer_or_admin = require_role(UserRole.REVIEWER, UserRole.ADMIN)


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), _: User = Depends(reviewer_or_admin)):
    cases = db.query(KYCCase).order_by(KYCCase.created_at.desc()).all()
    out = []
    for case in cases:
        risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case.id).first()
        out.append(
            {
                "case_id": str(case.id),
                "user_email": case.user.email,
                "status": case.status.value,
                "risk_level": risk.risk_level.value if risk and risk.risk_level else None,
                "fraud_risk_score": risk.fraud_risk_score if risk else None,
                "created_at": case.created_at.isoformat(),
            }
        )
    return out


@router.get("/cases/{case_id}")
def case_detail(case_id: str, db: Session = Depends(get_db), _: User = Depends(reviewer_or_admin)):
    case = db.query(KYCCase).filter(KYCCase.id == uuid.UUID(case_id)).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    ocr = db.query(OCRResult).filter(OCRResult.case_id == case.id).first()
    face = db.query(FaceVerification).filter(FaceVerification.case_id == case.id).first()
    liveness = db.query(LivenessResult).filter(LivenessResult.case_id == case.id).first()
    deepfake = db.query(DeepfakeResult).filter(DeepfakeResult.case_id == case.id).first()
    replay = db.query(ReplayResult).filter(ReplayResult.case_id == case.id).first()
    rppg = db.query(RPPGResult).filter(RPPGResult.case_id == case.id).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case.id).first()
    actions = db.query(ReviewerAction).filter(ReviewerAction.case_id == case.id).order_by(ReviewerAction.decided_at.desc()).all()

    def row(obj):
        if obj is None:
            return None
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        for k, v in d.items():
            if hasattr(v, "value") and not isinstance(v, (int, float, str, bool)):
                d[k] = v.value
            elif hasattr(v, "isoformat"):
                d[k] = v.isoformat()
            elif hasattr(v, "hex") and not isinstance(v, (bytes, bytearray)):
                d[k] = str(v)
        return d

    return {
        "case": {"id": str(case.id), "status": case.status.value, "user_email": case.user.email, "created_at": case.created_at.isoformat()},
        "document": row(ocr),
        "face": row(face),
        "liveness": row(liveness),
        "deepfake": row(deepfake),
        "replay": row(replay),
        "rppg": row(rppg),
        "risk": row(risk),
        "reviewer_actions": [row(a) for a in actions],
    }


@router.put("/cases/{case_id}/decision")
def submit_decision(
    case_id: str,
    payload: ReviewerDecisionIn,
    db: Session = Depends(get_db),
    reviewer: User = Depends(reviewer_or_admin),
):
    case = db.query(KYCCase).filter(KYCCase.id == uuid.UUID(case_id)).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    if payload.action not in ReviewerActionType.__members__:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action must be APPROVE, REJECT, or MANUAL_REVIEW.")

    action = ReviewerAction(
        id=uuid.uuid4(),
        case_id=case.id,
        reviewer_id=reviewer.id,
        action=ReviewerActionType(payload.action),
        notes=payload.notes,
    )
    db.add(action)

    from app.models.kyc_case import CaseStatus

    case.status = {
        "APPROVE": CaseStatus.VERIFIED,
        "REJECT": CaseStatus.REJECTED,
        "MANUAL_REVIEW": CaseStatus.MANUAL_REVIEW,
    }[payload.action]
    db.commit()
    db.refresh(action)

    return {"case_id": str(case.id), "new_status": case.status.value, "reviewer_action_id": str(action.id)}
