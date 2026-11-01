"""
Turn real/fake VIDEOS into a face-crop frame dataset for training.

    python prepare_deepfake_dataset.py --real /data/ffpp/original --fake /data/ffpp/Deepfakes \
        --out /data/deepfake_frames --every 10 --max-per-video 20

Output layout (what train_deepfake_model.py expects):
    <out>/real/<videoid>__<frameno>.jpg
    <out>/fake/<videoid>__<frameno>.jpg

The `<videoid>__` prefix is what the trainer uses to keep ALL frames of one
video (and, if you name them so, one identity) in the SAME split --
splitting frame-by-frame would leak near-identical frames across
train/val/test and inflate every metric.

Face cropping uses app.ml.deepfake.crop_face -- the very function the
backend uses at prediction time -- so training and serving inputs match.
Requires: opencv-python, mediapipe (same as the backend venv).
"""
import argparse
import os
import sys

import cv2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))
from app.ml.deepfake import crop_face  # noqa: E402

VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv", ".webm")


def process_folder(src: str, dst: str, every: int, max_per_video: int, prefix: str = "") -> int:
    os.makedirs(dst, exist_ok=True)
    saved = 0
    for root, _, files in os.walk(src):
        for name in sorted(files):
            if not name.lower().endswith(VIDEO_EXT):
                continue
            vid = prefix + os.path.splitext(name)[0].replace("__", "_")
            cap = cv2.VideoCapture(os.path.join(root, name))
            idx, n = 0, 0
            while n < max_per_video:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % every == 0:
                    face = crop_face(frame)
                    if face is not None and face.size:
                        cv2.imwrite(os.path.join(dst, f"{vid}__{idx:05d}.jpg"), face)
                        saved += 1
                        n += 1
                idx += 1
            cap.release()
    return saved


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", required=True, help="folder of REAL (pristine) videos")
    ap.add_argument("--fake", required=True, help="folder of FAKE (manipulated) videos")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=10, help="take every Nth frame")
    ap.add_argument("--max-per-video", type=int, default=20)
    a = ap.parse_args()
    r = process_folder(a.real, os.path.join(a.out, "real"), a.every, a.max_per_video)
    f = process_folder(a.fake, os.path.join(a.out, "fake"), a.every, a.max_per_video)
    print(f"Saved {r} real and {f} fake face crops to {a.out}")
