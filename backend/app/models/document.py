import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

# Use native JSONB on Postgres in production, but fall back to portable
# JSON on other dialects (e.g. SQLite, used for local/dev/test runs).
JSONType = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import relationship

from app.core.database import Base


class Document(Base):
    """
    Metadata about an uploaded identity document.
    `file_ref_temp` points at a temporary on-disk location; nothing
    sensitive about the document image itself is duplicated elsewhere.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String(64), nullable=True)  # e.g. "ID_CARD", "PASSPORT" (heuristically classified)
    original_filename = Column(String(255), nullable=False)
    file_ref_temp = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="documents")
    ocr_result = relationship("OCRResult", back_populates="document", uselist=False, cascade="all, delete-orphan")


class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("kyc_cases.id", ondelete="CASCADE"), nullable=False, unique=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    extracted_name = Column(String(255), nullable=True)
    extracted_dob = Column(String(64), nullable=True)
    extracted_doc_number = Column(String(128), nullable=True)
    raw_text_blocks = Column(JSONType, nullable=True)  # all OCR text fragments + confidence

    authenticity_score = Column(Float, nullable=True)   # 0-100
    tampering_flag = Column(Boolean, nullable=True)
    tampering_probability = Column(Float, nullable=True)  # 0-1
    suspicious_regions = Column(JSONType, nullable=True)   # list of bounding boxes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("KYCCase", back_populates="ocr_result")
    document = relationship("Document", back_populates="ocr_result")
