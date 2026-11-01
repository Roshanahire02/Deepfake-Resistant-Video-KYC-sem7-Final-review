"""
Re-evaluate a trained deepfake checkpoint on any labeled frame folder
(<data>/real/*.jpg, <data>/fake/*.jpg -- same layout as training), e.g. on a
DIFFERENT dataset than you trained on to measure cross-dataset generalization.

    python evaluate_deepfake.py --data /data/celebdf_frames --checkpoint ../../backend/storage/models/deepfake_effnet.pt

Cross-dataset results are usually much lower than same-dataset ones -- report both.
"""
import argparse
import json
import os
import sys

import numpy as np
import torch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "backend"))
from metrics import classification_metrics  # noqa: E402
from app.ml.deepfake import preprocess_frame  # noqa: E402  (identical preprocessing to serving)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", default="deepfake_eval.json")
    a = ap.parse_args()
    from torchvision.models import efficientnet_b0

    model = efficientnet_b0(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 2)
    model.load_state_dict(torch.load(a.checkpoint, map_location="cpu"))
    model.eval()
    ys, ps = [], []
    for label, cls in ((0, "real"), (1, "fake")):
        d = os.path.join(a.data, cls)
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            bgr = np.array(Image.open(os.path.join(d, f)).convert("RGB"))[:, :, ::-1].copy()
            with torch.no_grad():
                ps.append(float(torch.softmax(model(preprocess_frame(bgr)), 1)[0, 1]))
            ys.append(label)
    m = classification_metrics(ys, ps)
    print(json.dumps(m, indent=2))
    json.dump({"dataset": a.data, "test": m}, open(a.out, "w"), indent=2)
