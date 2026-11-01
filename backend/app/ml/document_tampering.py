"""
Model A (part 2) — Document tampering / authenticity baseline.

This is an *academic baseline*, not a forensic-grade tool. It combines
three classical, explainable signals:

1. Error Level Analysis (ELA): re-compresses the image at a known JPEG
   quality and diffs it against the original. Regions that were
   locally edited/pasted tend to have a different compression-error
   signature than the rest of the (uniformly compressed) image.
2. Noise-inconsistency analysis: estimates local noise variance across
   a grid of patches. Spliced regions often have different sensor
   noise than the surrounding image.
3. Edge/copy-move heuristic: looks for duplicated blocks via a coarse
   block-hash comparison, a common indicator of copy-paste tampering
   (e.g. duplicating a photo or a digit).

Each signal is normalized to [0, 1] and combined into a single
`tampering_probability`. This is deliberately transparent so it can be
explained in a viva, rather than an opaque black-box score.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


def _error_level_analysis(image_bgr: np.ndarray, quality: int = 90) -> Tuple[np.ndarray, float]:
    ok, encoded = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return np.zeros_like(image_bgr[:, :, 0], dtype=np.float32), 0.0
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(image_bgr, recompressed).astype(np.float32)
    ela_map = diff.mean(axis=2)
    # Normalize map and compute a "spread" score: high std => uneven compression error => suspicious
    if ela_map.max() > 0:
        ela_norm = ela_map / ela_map.max()
    else:
        ela_norm = ela_map
    score = float(np.clip(ela_norm.std() * 4.0, 0.0, 1.0))
    return ela_norm, score


def _noise_inconsistency(image_bgr: np.ndarray, patch_size: int = 32) -> Tuple[float, List[Dict[str, Any]]]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    h, w = gray.shape
    variances = []
    regions = []
    for y in range(0, h - patch_size, patch_size):
        for x in range(0, w - patch_size, patch_size):
            patch = gray[y : y + patch_size, x : x + patch_size]
            lap = cv2.Laplacian(patch, cv2.CV_32F)
            var = float(lap.var())
            variances.append(var)
            regions.append({"x": x, "y": y, "w": patch_size, "h": patch_size, "noise_var": var})
    if not variances:
        return 0.0, []
    arr = np.array(variances)
    mean, std = arr.mean(), arr.std() + 1e-6
    # Flag patches whose noise variance deviates strongly from the image-wide mean
    outliers = [r for r in regions if abs(r["noise_var"] - mean) > 2.0 * std]
    score = float(np.clip(len(outliers) / max(len(regions), 1) * 3.0, 0.0, 1.0))
    return score, outliers


def _copy_move_heuristic(image_bgr: np.ndarray, block_size: int = 16, hash_bits: int = 8) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    hashes: Dict[bytes, int] = {}
    duplicates = 0
    total = 0
    for y in range(0, h - block_size, block_size):
        for x in range(0, w - block_size, block_size):
            block = gray[y : y + block_size, x : x + block_size]
            small = cv2.resize(block, (hash_bits, hash_bits), interpolation=cv2.INTER_AREA)
            bits = (small > small.mean()).astype(np.uint8)
            key = bits.tobytes()
            total += 1
            if key in hashes:
                duplicates += 1
            else:
                hashes[key] = 1
    if total == 0:
        return 0.0
    # Some duplication is normal (flat backgrounds); only flag if notably high
    ratio = duplicates / total
    score = float(np.clip((ratio - 0.05) / 0.25, 0.0, 1.0))
    return score


def analyze_tampering(image_bgr: np.ndarray) -> Dict[str, Any]:
    """
    Combine ELA, noise-inconsistency, and copy-move signals into a single
    tampering_probability + authenticity_score, with suspicious regions
    surfaced for the reviewer UI.
    """
    _, ela_score = _error_level_analysis(image_bgr)
    noise_score, noise_regions = _noise_inconsistency(image_bgr)
    copy_move_score = _copy_move_heuristic(image_bgr)

    # Weighted combination — weights are configuration, easy to justify/tune in the report
    weights = {"ela": 0.4, "noise": 0.35, "copy_move": 0.25}
    tampering_probability = (
        weights["ela"] * ela_score + weights["noise"] * noise_score + weights["copy_move"] * copy_move_score
    )
    tampering_probability = float(np.clip(tampering_probability, 0.0, 1.0))
    authenticity_score = round((1.0 - tampering_probability) * 100, 2)
    tampering_flag = tampering_probability >= 0.5

    suspicious_regions = [
        {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"], "reason": "noise_inconsistency"}
        for r in noise_regions[:10]  # cap for UI readability
    ]

    return {
        "authenticity_score": authenticity_score,
        "tampering_probability": round(tampering_probability, 4),
        "tampering_flag": tampering_flag,
        "suspicious_regions": suspicious_regions,
        "signal_breakdown": {
            "error_level_analysis": round(ela_score, 4),
            "noise_inconsistency": round(noise_score, 4),
            "copy_move_heuristic": round(copy_move_score, 4),
        },
    }
