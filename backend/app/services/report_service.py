"""
Verification report generation (Objective 4 / final workflow step).

Freezes a snapshot of every module's results at the moment of
generation into `verification_reports.report_snapshot`. Deliberately
excludes any raw video/image bytes -- only structured metadata that
was already persisted by the upstream services is included, in line
with the "no raw biometric video stored" privacy requirement.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import OCRResult
from app.models.kyc_case import KYCCase
from app.models.results import (
    DeepfakeResult,
    FaceVerification,
    LivenessResult,
    ReplayResult,
    RiskAssessment,
    RPPGResult,
    VerificationReport,
)


def _row(obj) -> dict | None:
    if obj is None:
        return None
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in data.items():
        if hasattr(v, "value") and not isinstance(v, (int, float, str, bool)):
            data[k] = v.value
        elif hasattr(v, "isoformat"):
            data[k] = v.isoformat()
        elif hasattr(v, "hex") and not isinstance(v, (bytes, bytearray)):
            try:
                data[k] = str(v)
            except Exception:
                pass
    return data


def generate_report(db: Session, case: KYCCase) -> VerificationReport:
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case.id).first()
    if not risk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fraud risk must be calculated before a verification report can be generated.",
        )

    ocr = db.query(OCRResult).filter(OCRResult.case_id == case.id).first()
    face = db.query(FaceVerification).filter(FaceVerification.case_id == case.id).first()
    liveness = db.query(LivenessResult).filter(LivenessResult.case_id == case.id).first()
    deepfake = db.query(DeepfakeResult).filter(DeepfakeResult.case_id == case.id).first()
    replay = db.query(ReplayResult).filter(ReplayResult.case_id == case.id).first()
    rppg = db.query(RPPGResult).filter(RPPGResult.case_id == case.id).first()

    snapshot = {
        "case_id": str(case.id),
        "case_status": case.status.value,
        "document": _row(ocr),
        "face_verification": _row(face),
        "liveness": _row(liveness),
        "deepfake": _row(deepfake),
        "replay": _row(replay),
        "rppg": _row(rppg),
        "risk_assessment": _row(risk),
    }

    existing = db.query(VerificationReport).filter(VerificationReport.case_id == case.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    report = VerificationReport(id=uuid.uuid4(), case_id=case.id, report_snapshot=snapshot)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
