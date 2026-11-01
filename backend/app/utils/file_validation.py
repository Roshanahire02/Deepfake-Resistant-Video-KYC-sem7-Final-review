"""File upload validation: type + size checks used by the document API."""
from fastapi import HTTPException, UploadFile

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
ALLOWED_DOC_TYPES = ALLOWED_IMAGE_TYPES | {"application/pdf"}


def validate_upload(file: UploadFile, max_mb: int, allow_pdf: bool = True) -> None:
    allowed = ALLOWED_DOC_TYPES if allow_pdf else ALLOWED_IMAGE_TYPES
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Allowed: {', '.join(sorted(allowed))}",
        )
    # size checked by caller after reading bytes (UploadFile doesn't expose size pre-read reliably)


def validate_size(raw_bytes: bytes, max_mb: int) -> None:
    max_bytes = max_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File exceeds maximum size of {max_mb}MB")
    if len(raw_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
