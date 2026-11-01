"""
Evaluate liveness (blink / head-turn) on a LABELED video set -> APCER/BPCER/ACER.

    python evaluate_liveness.py --manifest manifest.csv --out liveness_eval.json

manifest.csv columns:  path,label,challenge
    label     = genuine | attack      (you must record/collect these yourself,
                                       e.g. genuine live clips + phone-replay /
                                       printed-photo attack clips; or use a public
                                       anti-spoofing dataset whose licence you accept)
    challenge = BLINK_TWICE | TURN_LEFT | TURN_RIGHT   (the challenge the clip was for)

A clip counts as "accepted as live" when app.ml.liveness reports passed=True.
Run it from the backend venv (needs opencv + mediapipe).
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
from metrics import pad_metrics  # noqa: E402
from app.ml.liveness import analyze_liveness  # noqa: E402


def read_frames(path, max_frames=90):
    cap, frames = cv2.VideoCapture(path), []
    while len(frames) < max_frames:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    return frames


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", default="liveness_eval.json")
    a = ap.parse_args()
    is_attack, accepted = [], []
    with open(a.manifest) as fh:
        for row in csv.DictReader(fh):
            frames = read_frames(row["path"])
            if not frames:
                print("skip unreadable:", row["path"])
                continue
            res = analyze_liveness(frames, row["challenge"])
            is_attack.append(row["label"].strip().lower() == "attack")
            accepted.append(bool(res.get("passed")))
    out = pad_metrics(is_attack, accepted)
    print(json.dumps(out, indent=2))
    json.dump({**out, "note": "Evaluated on the manifest provided; describes that set only."}, open(a.out, "w"), indent=2)
