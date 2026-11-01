from typing import Any, List, Optional

from pydantic import BaseModel


class OCRFieldResult(BaseModel):
    text: str
    confidence: float


class DocumentAnalysisOut(BaseModel):
    document_id: str
    extracted_name: Optional[str] = None
    extracted_dob: Optional[str] = None
    extracted_doc_number: Optional[str] = None
    doc_type: Optional[str] = None
    authenticity_score: Optional[float] = None
    tampering_flag: Optional[bool] = None
    tampering_probability: Optional[float] = None
    suspicious_regions: Optional[List[Any]] = None
    raw_text_blocks: Optional[List[Any]] = None
