"""
Model A (part 1) — Document OCR.

Wraps EasyOCR to extract raw text blocks from an identity-document
image, then applies simple regex/heuristic field parsing to pull out
a name, date of birth, and document number.

This is intentionally a *generic* field parser: identity document
layouts vary hugely, so a real product would use a per-document-type
template. For the academic prototype, we parse using common patterns
(date-like strings, labeled fields such as "Name:"/"DOB:") and report
per-field confidence from the OCR engine itself, so the reviewer can
see when extraction is unreliable rather than trusting an unlabeled
guess.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Dict, List

import cv2
import numpy as np

DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b"
)
DOC_NUMBER_PATTERN = re.compile(r"\b[A-Z0-9]{6,20}\b")
NAME_LABELS = ("name", "full name", "given name", "surname")
DOB_LABELS = ("dob", "date of birth", "birth")
DOC_NUM_LABELS = ("no", "number", "id no", "document no", "card no")


@lru_cache(maxsize=1)
def _get_reader():
    """
    EasyOCR downloads its detection/recognition weights on first use.
    Cached as a singleton so the model loads once per process
    (see app.main startup event).
    """
    import easyocr  # imported lazily so the API can boot even if easyocr/torch aren't installed yet

    return easyocr.Reader(["en"], gpu=False)


def preprocess_image(image_bgr: np.ndarray) -> np.ndarray:
    """Light preprocessing to improve OCR reliability: grayscale + adaptive threshold + denoise."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    # CLAHE improves contrast on scanned/photographed documents
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    return enhanced


def run_ocr(image_bgr: np.ndarray) -> List[Dict[str, Any]]:
    """Run EasyOCR and return raw text blocks with bounding boxes + confidence."""
    reader = _get_reader()
    preprocessed = preprocess_image(image_bgr)
    results = reader.readtext(preprocessed)
    blocks = []
    for bbox, text, conf in results:
        blocks.append(
            {
                "text": text,
                "confidence": round(float(conf), 4),
                "bbox": [[float(p[0]), float(p[1])] for p in bbox],
            }
        )
    return blocks


def parse_fields(blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Heuristic field extraction from raw OCR text blocks.
    Looks for label/value adjacency and generic patterns.
    """
    full_text_lines = [b["text"] for b in blocks]
    joined = " ".join(full_text_lines)

    extracted_name = None
    extracted_dob = None
    extracted_doc_number = None

    # Date of birth: first date-like token found
    date_match = DATE_PATTERN.search(joined)
    if date_match:
        extracted_dob = date_match.group(0)

    # Document number: prefer a labeled line, else the longest alnum token
    for i, line in enumerate(full_text_lines):
        lower = line.lower()
        if any(lbl in lower for lbl in DOC_NUM_LABELS):
            # value is likely on the same or next line
            candidates = DOC_NUMBER_PATTERN.findall(line.upper())
            if not candidates and i + 1 < len(full_text_lines):
                candidates = DOC_NUMBER_PATTERN.findall(full_text_lines[i + 1].upper())
            if candidates:
                extracted_doc_number = candidates[0]
                break
    if not extracted_doc_number:
        all_candidates = DOC_NUMBER_PATTERN.findall(joined.upper())
        # filter out pure-date-looking numbers
        all_candidates = [c for c in all_candidates if not c.isdigit() or len(c) >= 8]
        if all_candidates:
            extracted_doc_number = max(all_candidates, key=len)

    # Name: prefer a labeled line, else the longest alphabetic-only line
    for i, line in enumerate(full_text_lines):
        lower = line.lower()
        if any(lbl in lower for lbl in NAME_LABELS):
            if i + 1 < len(full_text_lines) and full_text_lines[i + 1].replace(" ", "").isalpha():
                extracted_name = full_text_lines[i + 1].strip()
            else:
                # strip the label itself off the line
                stripped = re.sub(r"(?i)(name|full name|given name|surname)\s*[:\-]?", "", line).strip()
                if stripped:
                    extracted_name = stripped
            break
    if not extracted_name:
        alpha_lines = [l for l in full_text_lines if l.replace(" ", "").isalpha() and len(l) > 4]
        if alpha_lines:
            extracted_name = max(alpha_lines, key=len).strip()

    return {
        "extracted_name": extracted_name,
        "extracted_dob": extracted_dob,
        "extracted_doc_number": extracted_doc_number,
    }


def classify_document_type(blocks: List[Dict[str, Any]]) -> str:
    """Very lightweight keyword-based document type classifier."""
    joined = " ".join(b["text"].lower() for b in blocks)
    if "passport" in joined:
        return "PASSPORT"
    if "driving" in joined or "licence" in joined or "license" in joined:
        return "DRIVING_LICENSE"
    if "identity" in joined or "id card" in joined or "national id" in joined:
        return "ID_CARD"
    return "UNKNOWN"


def extract_document_info(image_bgr: np.ndarray) -> Dict[str, Any]:
    """Full OCR pipeline entry point used by the document service."""
    blocks = run_ocr(image_bgr)
    fields = parse_fields(blocks)
    doc_type = classify_document_type(blocks)
    avg_conf = (
        round(sum(b["confidence"] for b in blocks) / len(blocks), 4) if blocks else 0.0
    )
    return {
        "raw_text_blocks": blocks,
        "doc_type": doc_type,
        "ocr_average_confidence": avg_conf,
        **fields,
    }
