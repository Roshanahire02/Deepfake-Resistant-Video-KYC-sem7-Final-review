"""
Builds a clearly-labelled MOCK identity card image from YOUR OWN selfie, so you
can demonstrate document upload + face matching without any real ID document.

    python tools/make_sample_id.py my_selfie.jpg "YOUR NAME" 2000-01-31 --out sample_id.png

Use a photo of yourself (or someone who consented). The card says "DEMO ID --
NOT A REAL DOCUMENT" and imitates no real government card. Needs only OpenCV.
"""
import argparse
import sys

import cv2
import numpy as np


def make_card(selfie_path: str, name: str, dob: str, number: str) -> np.ndarray:
    selfie = cv2.imread(selfie_path)
    if selfie is None:
        sys.exit(f"Could not read image: {selfie_path}")
    card = np.full((540, 856, 3), 245, np.uint8)
    cv2.rectangle(card, (0, 0), (855, 70), (150, 90, 30), -1)
    cv2.putText(card, "DEMO IDENTITY CARD", (24, 47), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    # photo: centre-crop to 3:4 and resize
    h, w = selfie.shape[:2]
    tw = min(w, int(h * 0.75))
    x0 = (w - tw) // 2
    photo = cv2.resize(selfie[:, x0:x0 + tw], (240, 320))
    card[120:440, 40:280] = photo
    cv2.rectangle(card, (40, 120), (280, 440), (90, 90, 90), 2)
    for i, (label, value) in enumerate((("NAME", name.upper()), ("DATE OF BIRTH", dob), ("ID NUMBER", number))):
        y = 170 + i * 95
        cv2.putText(card, label, (320, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (110, 110, 110), 1, cv2.LINE_AA)
        cv2.putText(card, value, (320, y + 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2, cv2.LINE_AA)
    cv2.putText(card, "DEMO ID - NOT A REAL DOCUMENT", (190, 505), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 190), 2, cv2.LINE_AA)
    return card


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("selfie")
    ap.add_argument("name")
    ap.add_argument("dob", help="e.g. 2000-01-31")
    ap.add_argument("--number", default="DEMO-1234567")
    ap.add_argument("--out", default="sample_id.png")
    a = ap.parse_args()
    cv2.imwrite(a.out, make_card(a.selfie, a.name, a.dob, a.number))
    print("Wrote", a.out)
