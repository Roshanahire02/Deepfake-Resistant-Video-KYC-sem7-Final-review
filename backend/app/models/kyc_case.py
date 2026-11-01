import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CaseStatus(str, enum.Enum):
    CREATED = "CREATED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_ANALYZED = "DOCUMENT_ANALYZED"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    RISK_CALCULATED = "RISK_CALCULATED"
    VERIFIED = "VERIFIED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FLAGGED = "FLAGGED"
    REJECTED = "REJECTED"


class KYCCase(Base):
    __tablename__ = "kyc_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(CaseStatus), nullable=False, default=CaseStatus.CREATED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="kyc_cases")
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    ocr_result = relationship("OCRResult", back_populates="case", uselist=False, cascade="all, delete-orphan")
    face_verification = relationship("FaceVerification", back_populates="case", uselist=False, cascade="all, delete-orphan")
    liveness_result = relationship("LivenessResult", back_populates="case", uselist=False, cascade="all, delete-orphan")
    deepfake_result = relationship("DeepfakeResult", back_populates="case", uselist=False, cascade="all, delete-orphan")
    replay_result = relationship("ReplayResult", back_populates="case", uselist=False, cascade="all, delete-orphan")
    rppg_result = relationship("RPPGResult", back_populates="case", uselist=False, cascade="all, delete-orphan")
    risk_assessment = relationship("RiskAssessment", back_populates="case", uselist=False, cascade="all, delete-orphan")
    report = relationship("VerificationReport", back_populates="case", uselist=False, cascade="all, delete-orphan")
    reviewer_actions = relationship("ReviewerAction", back_populates="case", cascade="all, delete-orphan")
