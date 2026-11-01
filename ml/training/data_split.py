"""Leak-free dataset listing/splitting (no torch needed, so it is unit-tested)."""
import os

import numpy as np
from sklearn.model_selection import GroupShuffleSplit


def list_samples(root):
    samples = []
    for label, cls in ((0, "real"), (1, "fake")):
        d = os.path.join(root, cls)
        if not os.path.isdir(d):
            raise SystemExit(f"Missing folder: {d}  (see prepare_deepfake_dataset.py)")
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                group = f"{cls}:{f.split('__')[0]}"  # video id, kept per class
                samples.append((os.path.join(d, f), label, group))
    if not samples:
        raise SystemExit("No images found.")
    return samples


def group_split(samples, seed=42):
    """70/15/15 split where every frame of a video lands in exactly one split."""
    groups = np.array([s[2] for s in samples])
    idx = np.arange(len(samples))
    train_idx, rest_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=seed).split(idx, groups=groups))
    val_rel, test_rel = next(GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=seed).split(rest_idx, groups=groups[rest_idx]))
    parts = (train_idx, rest_idx[val_rel], rest_idx[test_rel])
    sets = [set(groups[i] for i in p) for p in parts]
    assert not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]), "group leakage between splits!"
    return tuple([samples[i] for i in p] for p in parts)
