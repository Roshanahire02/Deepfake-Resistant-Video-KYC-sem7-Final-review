from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document, OCRResult
from app.models.kyc_case import CaseStatus, KYCCase
from app.models.results import DeepfakeResult, FaceVerification, LivenessResult, ReplayResult, RiskAssessment, RPPGResult
from app.models.user import User
from app.schemas.deepfake import DeepfakeResultOut
from app.schemas.document import DocumentAnalysisOut
from app.schemas.face import FaceVerificationOut
from app.schemas.kyc import KYCCaseOut, KYCCaseSummary
from app.schemas.liveness import LivenessResultOut
from app.schemas.replay import ReplayResultOut
from app.schemas.risk import RiskAssessmentOut
from app.schemas.rppg import RPPGResultOut
from app.services import document_service, progress, report_service
from app.services.kyc_pipeline_service import run_video_pipeline
from app.utils.temp_file_manager import delete_path, save_temp_bytes
from app.utils.video_frames import extract_frames

router = APIRouter(prefix="/api/kyc", tags=["kyc"])

VALID_CHALLENGES = {"BLINK_TWICE", "TURN_LEFT", "TURN_RIGHT"}
ALLOWED_VIDEO_TYPES = {"video/webm", "video/mp4", "video/quicktime", "video/x-matroska"}


def _get_owned_case(db: Session, case_id: str, user: User) -> KYCCase:
    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case id.")
    case = db.query(KYCCase).filter(KYCCase.id == cid).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="KYC case not found.")
    if case.user_id != user.id and user.role.value == "USER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this case.")
    return case


@router.post("/create", response_model=KYCCaseOut, status_code=status.HTTP_201_CREATED)
def create_case(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = KYCCase(id=uuid.uuid4(), user_id=user.id, status=CaseStatus.CREATED)
    db.add(case)
    db.commit()
    db.refresh(case)
    return KYCCaseOut(id=str(case.id), status=case.status.value, created_at=case.created_at, updated_at=case.updated_at)


@router.get("/dashboard/summary", response_model=KYCCaseSummary)
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = db.query(KYCCase).filter(KYCCase.user_id == user.id).all()
    total = len(cases)
    verified = sum(1 for c in cases if c.status == CaseStatus.VERIFIED)
    flagged = sum(1 for c in cases if c.status in (CaseStatus.FLAGGED, CaseStatus.REJECTED))
    pending = total - verified - flagged
    return KYCCaseSummary(total_cases=total, verified=verified, pending=pending, flagged=flagged)


@router.get("/list")
def list_my_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    cases = db.query(KYCCase).filter(KYCCase.user_id == user.id).order_by(KYCCase.created_at.desc()).all()
    return [
        {"id": str(c.id), "status": c.status.value, "created_at": c.created_at.isoformat()}
        for c in cases
    ]


@router.post("/document/upload")
def upload_document(
    case_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, user)
    document = document_service.upload_document(db, case, file)
    return {"document_id": str(document.id), "case_status": case.status.value}


@router.post("/document/analyze", response_model=DocumentAnalysisOut)
def analyze_document(
    case_id: str = Form(...),
    document_id: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, user)
    document = db.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    result = document_service.analyze_document(db, case, document)
    return DocumentAnalysisOut(
        document_id=str(document.id),
        extracted_name=result.extracted_name,
        extracted_dob=result.extracted_dob,
        extracted_doc_number=result.extracted_doc_number,
        doc_type=document.doc_type,
        authenticity_score=result.authenticity_score,
        tampering_flag=result.tampering_flag,
        tampering_probability=result.tampering_probability,
        suspicious_regions=result.suspicious_regions,
        raw_text_blocks=result.raw_text_blocks,
    )


@router.post("/video/process")
def process_video(
    case_id: str = Form(...),
    challenge_type: str = Form(...),
    consent: bool = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Single entry point for the whole video-KYC stage: liveness, deepfake,
    replay and face-matching, followed by fraud risk calculation. The
    uploaded clip is written to a temp path, analyzed, and guaranteed to
    be deleted before this handler returns -- it is never persisted.
    """
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent to temporary video processing is required before Video KYC can proceed.",
        )
    if challenge_type not in VALID_CHALLENGES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"challenge_type must be one of {VALID_CHALLENGES}")
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported video type '{file.content_type}'.")

    case = _get_owned_case(db, case_id, user)

    raw = file.file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 20 * 1024 * 1024  # video allowance, generous vs. still-image cap
    if len(raw) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded video is empty.")
    if len(raw) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded video exceeds the size limit.")

    ext = ".webm" if "webm" in (file.content_type or "") else ".mp4"
    temp_path = save_temp_bytes(raw, settings.TEMP_VIDEO_DIR, ext)

    progress.start(case.id)
    ok = False
    try:
        frames, fps = extract_frames(temp_path, max_frames=150)
        result = run_video_pipeline(db, case, frames, challenge_type, fps=fps)
        ok = True
    finally:
        progress.finish(case.id, ok=ok)
        delete_path(temp_path)  # raw video is NEVER retained beyond this request

    return result


@router.post("/risk/calculate", response_model=RiskAssessmentOut)
def recalculate_risk(case_id: str = Form(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Re-derives the fraud risk score from the already-persisted upstream
    results (useful if RISK_LOW_MAX/RISK_MEDIUM_MAX thresholds were
    changed, without re-running the whole video pipeline).
    """
    case = _get_owned_case(db, case_id, user)
    from app.ml.risk_engine import compute_risk
    from app.models.results import Decision, RiskLevel

    ocr = db.query(OCRResult).filter(OCRResult.case_id == case.id).first()
    face = db.query(FaceVerification).filter(FaceVerification.case_id == case.id).first()
    liveness = db.query(LivenessResult).filter(LivenessResult.case_id == case.id).first()
    deepfake = db.query(DeepfakeResult).filter(DeepfakeResult.case_id == case.id).first()
    replay = db.query(ReplayResult).filter(ReplayResult.case_id == case.id).first()

    if not (ocr and face and liveness and deepfake and replay):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document analysis and Video KYC must both be completed first.")

    # Rebuild the same inputs the live pipeline used. Checks that were
    # unavailable when the case was processed stay unavailable here (never
    # silently counted as a clean 0), and rPPG is included like in the
    # main pipeline so both paths give the same answer.
    unavailable = {}
    if deepfake.deepfake_probability is None:
        unavailable["deepfake"] = {
            "TRAINING_REQUIRED": "model not trained",
            "NO_FACE_FRAMES": "no face found in sampled frames",
        }.get(deepfake.status, "required library not installed")
    if face.similarity_score is None:
        unavailable["face_match"] = "face recognition library not installed"
    features = {
        "document_authenticity_score": ocr.authenticity_score or 0.0,
        "tampering_probability": ocr.tampering_probability or 0.0,
        "face_similarity": face.similarity_score,
        "face_quality": face.face_quality_score,
        "liveness_passed": bool(liveness.passed),
        "deepfake_probability": deepfake.deepfake_probability,
        "replay_probability": replay.replay_probability or 0.0,
    }
    rppg_row = db.query(RPPGResult).filter(RPPGResult.case_id == case.id).first()
    rppg_input = (
        {"status": rppg_row.status, "rppg_score": rppg_row.rppg_score, "heart_rate_bpm": rppg_row.heart_rate_bpm}
        if rppg_row else None
    )
    risk = compute_risk(features, rppg=rppg_input, unavailable=unavailable)

    existing = db.query(RiskAssessment).filter(RiskAssessment.case_id == case.id).first()
    if existing:
        db.delete(existing)
        db.flush()
    assessment = RiskAssessment(
        id=uuid.uuid4(),
        case_id=case.id,
        fraud_risk_score=risk["fraud_risk_score"],
        risk_level=RiskLevel(risk["risk_level"]),
        decision=Decision(risk["decision"]),
        feature_contributions=risk["feature_contributions"],
        explanation_text=risk["explanation_text"],
        model_version=risk["model_version"],
    )
    db.add(assessment)
    case.status = {"VERIFIED": CaseStatus.VERIFIED, "MANUAL_REVIEW": CaseStatus.MANUAL_REVIEW, "FLAGGED": CaseStatus.FLAGGED}.get(
        risk["decision"], CaseStatus.RISK_CALCULATED
    )
    db.commit()
    db.refresh(assessment)
    return RiskAssessmentOut(
        fraud_risk_score=assessment.fraud_risk_score,
        risk_level=assessment.risk_level.value,
        decision=assessment.decision.value,
        feature_contributions=assessment.feature_contributions,
        explanation_text=assessment.explanation_text,
        model_version=assessment.model_version,
    )


@router.get("/{case_id}/progress")
def get_progress(case_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Which pipeline stage is genuinely running for this case right now (see services/progress.py)."""
    case = _get_owned_case(db, case_id, user)
    info = progress.get(case.id)
    return {"stages": progress.STAGES, **(info or {"stage": None, "completed": [], "state": "IDLE"})}


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _get_owned_case(db, case_id, user)
    ocr = db.query(OCRResult).filter(OCRResult.case_id == case.id).first()
    face = db.query(FaceVerification).filter(FaceVerification.case_id == case.id).first()
    liveness = db.query(LivenessResult).filter(LivenessResult.case_id == case.id).first()
    deepfake = db.query(DeepfakeResult).filter(DeepfakeResult.case_id == case.id).first()
    replay = db.query(ReplayResult).filter(ReplayResult.case_id == case.id).first()
    rppg = db.query(RPPGResult).filter(RPPGResult.case_id == case.id).first()
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case.id).first()

    return {
        "id": str(case.id),
        "status": case.status.value,
        "created_at": case.created_at.isoformat(),
        "document": DocumentAnalysisOut(
            document_id=str(ocr.document_id), extracted_name=ocr.extracted_name, extracted_dob=ocr.extracted_dob,
            extracted_doc_number=ocr.extracted_doc_number, doc_type=None, authenticity_score=ocr.authenticity_score,
            tampering_flag=ocr.tampering_flag, tampering_probability=ocr.tampering_probability,
            suspicious_regions=ocr.suspicious_regions, raw_text_blocks=None,
        ) if ocr else None,
        "face": FaceVerificationOut(
            similarity_score=face.similarity_score, match_status=face.match_status,
            face_quality_score=face.face_quality_score, multiple_faces_detected=face.multiple_faces_detected,
            threshold_used=face.threshold_used,
        ) if face else None,
        "liveness": LivenessResultOut(
            challenge_type=liveness.challenge_type, passed=liveness.passed, motion_score=liveness.motion_score,
            blink_count=liveness.blink_count, confidence=liveness.confidence,
        ) if liveness else None,
        "deepfake": DeepfakeResultOut(
            deepfake_probability=deepfake.deepfake_probability, status=deepfake.status,
            frames_analyzed=deepfake.frames_analyzed, suspicious_frame_indices=deepfake.suspicious_frame_indices,
            model_version=deepfake.model_version,
        ) if deepfake else None,
        "replay": ReplayResultOut(
            replay_probability=replay.replay_probability, status=replay.status, signals=replay.signals,
        ) if replay else None,
        "rppg": RPPGResultOut(
            status=rppg.status, heart_rate_bpm=rppg.heart_rate_bpm, signal_quality=rppg.signal_quality,
            periodicity_score=rppg.periodicity_score, temporal_consistency=rppg.temporal_consistency,
            rppg_score=rppg.rppg_score, usable_frames=rppg.usable_frames, usable_frame_ratio=rppg.usable_frame_ratio,
            roi_stability=rppg.roi_stability, method_version=rppg.method_version, message=rppg.message,
        ) if rppg else None,
        "risk": RiskAssessmentOut(
            fraud_risk_score=risk.fraud_risk_score, risk_level=risk.risk_level.value if risk.risk_level else None,
            decision=risk.decision.value if risk.decision else None, feature_contributions=risk.feature_contributions,
            explanation_text=risk.explanation_text, model_version=risk.model_version,
        ) if risk else None,
    }


@router.get("/{case_id}/report")
def get_report(case_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _get_owned_case(db, case_id, user)
    report = report_service.generate_report(db, case)
    return {"case_id": str(case.id), "generated_at": report.generated_at.isoformat(), "report": report.report_snapshot}
