"""
Document upload + analysis orchestration (Objective 1).
"""
from __future__ import annotations

import os
import uuid

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.ml.document_ocr import extract_document_info
from app.ml.document_tampering import analyze_tampering
from app.models.document import Document, OCRResult
from app.models.kyc_case import CaseStatus, KYCCase
from app.utils.file_validation import validate_size, validate_upload
from app.utils.temp_file_manager import save_temp_bytes


def _is_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def _render_pdf_first_page(path: str, dpi: int = 200) -> np.ndarray:
    """
    Renders page 1 of a PDF to a BGR image so the same OCR / tampering /
    face-extraction pipeline used for photos can run on it. Only the
    first page is used (an ID document is a single page / card scan).
    """
    try:
        import pymupdf  # PyMuPDF
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF support is unavailable: PyMuPDF is not installed (pip install pymupdf). Upload a JPG/PNG instead.",
        ) from exc
    try:
        with pymupdf.open(path) as doc:
            if doc.page_count < 1:
                raise HTTPException(status_code=400, detail="The PDF has no pages.")
            pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            return cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    except HTTPException:
        raise
    except Exception as exc:  # corrupt / encrypted PDF
        raise HTTPException(status_code=400, detail="Could not read this PDF (corrupt or password-protected).") from exc


def load_image_bgr(path: str) -> np.ndarray:
    if _is_pdf(path):
        return _render_pdf_first_page(path)
    image = cv2.imread(path)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not read uploaded image (unsupported/corrupt file).")
    return image


def upload_document(db: Session, case: KYCCase, file: UploadFile) -> Document:
    validate_upload(file, settings.MAX_UPLOAD_MB, allow_pdf=True)
    raw = file.file.read()
    validate_size(raw, settings.MAX_UPLOAD_MB)
    # Don't trust the client-declared content type: confirm the bytes
    # really are a JPEG / PNG / PDF before storing anything.
    if not (raw[:3] == b"\xff\xd8\xff" or raw[:8] == b"\x89PNG\r\n\x1a\n" or raw[:5] == b"%PDF-"):
        raise HTTPException(status_code=400, detail="File content does not match a JPG, PNG or PDF document.")

    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    path = save_temp_bytes(raw, settings.UPLOAD_DIR, ext)

    document = Document(
        id=uuid.uuid4(),
        case_id=case.id,
        original_filename=file.filename or "document",
        file_ref_temp=path,
    )
    db.add(document)
    case.status = CaseStatus.DOCUMENT_UPLOADED
    db.commit()
    db.refresh(document)
    return document


def analyze_document(db: Session, case: KYCCase, document: Document) -> OCRResult:
    if document.case_id != case.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Document does not belong to this case.")

    image = load_image_bgr(document.file_ref_temp)

    try:
        ocr_info = extract_document_info(image)
    except ImportError as exc:
        # easyocr/torch not installed in this environment -- tampering
        # analysis (pure OpenCV) still runs below; OCR fields are
        # honestly reported as unavailable rather than fabricated.
        ocr_info = {
            "doc_type": None,
            "extracted_name": None,
            "extracted_dob": None,
            "extracted_doc_number": None,
            "raw_text_blocks": None,
            "ocr_average_confidence": None,
            "ocr_status": f"DEPENDENCY_UNAVAILABLE: {exc}",
        }

    tampering_info = analyze_tampering(image)

    document.doc_type = ocr_info["doc_type"]

    existing = db.query(OCRResult).filter(OCRResult.case_id == case.id).first()
    if existing:
        db.delete(existing)
        db.flush()

    result = OCRResult(
        id=uuid.uuid4(),
        case_id=case.id,
        document_id=document.id,
        extracted_name=ocr_info.get("extracted_name"),
        extracted_dob=ocr_info.get("extracted_dob"),
        extracted_doc_number=ocr_info.get("extracted_doc_number"),
        raw_text_blocks=ocr_info.get("raw_text_blocks"),
        authenticity_score=tampering_info["authenticity_score"],
        tampering_flag=tampering_info["tampering_flag"],
        tampering_probability=tampering_info["tampering_probability"],
        suspicious_regions=tampering_info["suspicious_regions"],
        notes=f"OCR avg confidence: {ocr_info.get('ocr_average_confidence')}",
    )
    db.add(result)
    case.status = CaseStatus.DOCUMENT_ANALYZED
    db.commit()
    db.refresh(result)
    return result
