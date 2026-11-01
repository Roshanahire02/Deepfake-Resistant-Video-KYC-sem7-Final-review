"""
Evaluate face matching on labeled image PAIRS -> similarity stats, FAR/FRR, EER.

    python evaluate_face_verification.py --pairs pairs.csv --threshold 0.55 --out face_eval.json

pairs.csv columns:  image_a,image_b,same_person      (same_person = 1 or 0)
Use a public benchmark (e.g. LFW pairs) or your own consented images. Requires
the backend venv with insightface + onnxruntime + mediapipe installed.
"""
import argparse
import csv
import json
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from metrics import equal_error_rate, far_frr  # noqa: E402
from app.ml.face_recognition import compare_faces  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--out", default="face_eval.json")
    a = ap.parse_args()
    same, sims, skipped = [], [], 0
    with open(a.pairs) as fh:
        for row in csv.DictReader(fh):
            ia, ib = cv2.imread(row["image_a"]), cv2.imread(row["image_b"])
            if ia is None or ib is None:
                skipped += 1
                continue
            r = compare_faces(ia, ib)
            if "similarity_score" not in r:  # no face found etc. -> excluded, and counted
                skipped += 1
                continue
            same.append(row["same_person"].strip() in ("1", "true", "True"))
            sims.append(r["similarity_score"])
    out = {**far_frr(same, sims, a.threshold), **equal_error_rate(same, sims), "pairs_skipped": skipped}
    print(json.dumps(out, indent=2))
    json.dump({**out, "note": "Describes the supplied pairs only."}, open(a.out, "w"), indent=2)
