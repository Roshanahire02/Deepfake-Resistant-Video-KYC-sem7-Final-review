import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

JSONType = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import relationship

from app.core.database import Base


class FaceVerification(Base):
    __tablename__ = "face_verification"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    similarity_score = Column(Float, nullable=True)     # cosine similarity, 0-1
    match_status = Column(String(32), nullable=True)    # MATCHED / NOT_MATCHED
    face_quality_score = Column(Float, nullable=True)   # 0-1
    multiple_faces_detected = Column(Boolean, default=False)
    threshold_used = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="face_verification")


class LivenessResult(Base):
    __tablename__ = "liveness_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    challenge_type = Column(String(64), nullable=True)  # BLINK_TWICE / TURN_LEFT / TURN_RIGHT
    passed = Column(Boolean, nullable=True)
    motion_score = Column(Float, nullable=True)
    blink_count = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="liveness_result")


class DeepfakeResult(Base):
    __tablename__ = "deepfake_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    deepfake_probability = Column(Float, nullable=True)  # 0-1, mean across analyzed frames
    status = Column(String(32), nullable=True)            # LOW_SUSPICION / MEDIUM_SUSPICION / HIGH_SUSPICION
    frames_analyzed = Column(Integer, nullable=True)
    suspicious_frame_indices = Column(JSONType, nullable=True)
    model_version = Column(String(64), nullable=True)
    gradcam_ref = Column(String(512), nullable=True)  # path to saved Grad-CAM overlay, if generated
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="deepfake_result")


class ReplayResult(Base):
    __tablename__ = "replay_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    replay_probability = Column(Float, nullable=True)
    status = Column(String(32), nullable=True)  # NOT_DETECTED / SUSPECTED / DETECTED
    signals = Column(JSONType, nullable=True)       # per-signal breakdown
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="replay_result")


class RPPGResult(Base):
    """
    Remote photoplethysmography result -- a physiological liveness
    signal (see app/ml/rppg.py). Only derived metadata is stored, same
    privacy contract as every other video-derived result: no raw
    signal waveform or video is ever persisted.
    """
    __tablename__ = "rppg_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    status = Column(String(32), nullable=True)  # AVAILABLE / INSUFFICIENT_SIGNAL / UNAVAILABLE / ERROR
    heart_rate_bpm = Column(Float, nullable=True)
    signal_quality = Column(Float, nullable=True)       # 0-1
    periodicity_score = Column(Float, nullable=True)    # 0-1
    temporal_consistency = Column(Float, nullable=True)  # 0-1
    rppg_score = Column(Float, nullable=True)            # 0-1, overall composite
    usable_frames = Column(Integer, nullable=True)
    usable_frame_ratio = Column(Float, nullable=True)
    roi_stability = Column(Float, nullable=True)
    method_version = Column(String(64), nullable=True)  # e.g. "CHROM"
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="rppg_result")


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Decision(str, enum.Enum):
    VERIFIED = "VERIFIED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    fraud_risk_score = Column(Float, nullable=True)      # 0-100
    risk_level = Column(Enum(RiskLevel), nullable=True)
    decision = Column(Enum(Decision), nullable=True)
    feature_contributions = Column(JSONType, nullable=True)  # SHAP values per feature
    explanation_text = Column(Text, nullable=True)
    model_version = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="risk_assessment")


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)

    report_snapshot = Column(JSONType, nullable=True)  # frozen copy of all results at generation time
    generated_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="report")


class ReviewerActionType(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ReviewerAction(Base):
    __tablename__ = "reviewer_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(Enum(ReviewerActionType), nullable=False)
    notes = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="reviewer_actions")
