"""Tests for ml/evaluation/metrics.py and ml/training/data_split.py (hand-computed expectations)."""
import os
import sys

import pytest

ML = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml")
sys.path.insert(0, os.path.join(ML, "evaluation"))
sys.path.insert(0, os.path.join(ML, "training"))

from data_split import group_split, list_samples  # noqa: E402
from metrics import classification_metrics, equal_error_rate, far_frr, pad_metrics  # noqa: E402


def test_pad_metrics_apcer_bpcer_acer():
    # 4 attacks (1 slipped through), 4 genuine (2 wrongly rejected)
    is_attack = [1, 1, 1, 1, 0, 0, 0, 0]
    accepted = [1, 0, 0, 0, 1, 1, 0, 0]
    m = pad_metrics(is_attack, accepted)
    assert m["APCER"] == 0.25 and m["BPCER"] == 0.5 and m["ACER"] == 0.375


def test_pad_metrics_missing_class_is_none_not_zero():
    m = pad_metrics([1, 1], [0, 0])
    assert m["BPCER"] is None and m["ACER"] is None


def test_far_frr_at_threshold():
    genuine = [1, 1, 1, 1, 0, 0, 0, 0]
    sim = [0.9, 0.8, 0.6, 0.4, 0.7, 0.3, 0.2, 0.1]
    m = far_frr(genuine, sim, 0.55)
    assert m["FRR"] == 0.25  # only 0.4 genuine rejected
    assert m["FAR"] == 0.25  # only 0.7 impostor accepted


def test_eer_perfectly_separable_is_zero():
    assert equal_error_rate([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1])["EER"] == 0.0


def test_classification_metrics_known_values():
    m = classification_metrics([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9])
    assert m["accuracy"] == 0.5 and m["confusion_matrix"] == [[1, 1], [1, 1]]
    assert m["roc_auc"] == 0.75


def test_group_split_never_leaks_a_video_across_splits(tmp_path):
    for cls in ("real", "fake"):
        d = tmp_path / cls
        d.mkdir()
        for vid in range(20):
            for frame in range(5):
                (d / f"vid{vid}__{frame:03d}.jpg").write_bytes(b"x")
    train, val, test = group_split(list_samples(str(tmp_path)))
    groups = [{s[2] for s in part} for part in (train, val, test)]
    assert not (groups[0] & groups[1]) and not (groups[0] & groups[2]) and not (groups[1] & groups[2])
    assert len(train) + len(val) + len(test) == 200
    # every frame of a video stays together
    for part in (train, val, test):
        counts = {}
        for s in part:
            counts[s[2]] = counts.get(s[2], 0) + 1
        assert all(c == 5 for c in counts.values())


def test_list_samples_requires_both_class_folders(tmp_path):
    (tmp_path / "real").mkdir()
    with pytest.raises(SystemExit):
        list_samples(str(tmp_path))
