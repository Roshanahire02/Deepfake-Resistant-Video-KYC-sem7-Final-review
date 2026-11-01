"""
Evaluation metrics for each module -- pure numpy/sklearn, unit-tested.

Standard definitions:
  Presentation-attack metrics (ISO/IEC 30107-3), for liveness / replay:
    APCER = attacks wrongly accepted as live / all attacks
    BPCER = genuine (bona fide) wrongly rejected / all genuine
    ACER  = (APCER + BPCER) / 2
  Face verification, at a similarity threshold:
    FAR = impostor pairs wrongly accepted / all impostor pairs
    FRR = genuine pairs wrongly rejected / all genuine pairs
    EER = operating point where FAR == FRR
"""
from __future__ import annotations

import numpy as np


def classification_metrics(y_true, y_score, threshold: float = 0.5) -> dict:
    from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

    y = np.asarray(y_true).astype(int)
    s = np.asarray(y_score, dtype=float)
    pred = (s >= threshold).astype(int)
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, s)) if len(set(y.tolist())) == 2 else None,
        "confusion_matrix": confusion_matrix(y, pred, labels=[0, 1]).tolist(),
    }


def pad_metrics(is_attack, accepted_as_live) -> dict:
    """is_attack[i]=True for presentation attacks; accepted_as_live[i]=True if the system passed it."""
    atk = np.asarray(is_attack, dtype=bool)
    acc = np.asarray(accepted_as_live, dtype=bool)
    n_attack, n_genuine = int(atk.sum()), int((~atk).sum())
    apcer = float((acc & atk).sum() / n_attack) if n_attack else None
    bpcer = float((~acc & ~atk).sum() / n_genuine) if n_genuine else None
    acer = (apcer + bpcer) / 2 if apcer is not None and bpcer is not None else None
    return {"APCER": apcer, "BPCER": bpcer, "ACER": acer, "n_attack": n_attack, "n_genuine": n_genuine}


def far_frr(is_genuine_pair, similarity, threshold: float) -> dict:
    g = np.asarray(is_genuine_pair, dtype=bool)
    s = np.asarray(similarity, dtype=float)
    accepted = s >= threshold
    n_imp, n_gen = int((~g).sum()), int(g.sum())
    return {
        "threshold": float(threshold),
        "FAR": float((accepted & ~g).sum() / n_imp) if n_imp else None,
        "FRR": float((~accepted & g).sum() / n_gen) if n_gen else None,
        "n_genuine_pairs": n_gen,
        "n_impostor_pairs": n_imp,
    }


def equal_error_rate(is_genuine_pair, similarity) -> dict:
    s = np.asarray(similarity, dtype=float)
    best = None
    for t in np.unique(s):
        m = far_frr(is_genuine_pair, s, t)
        if m["FAR"] is None or m["FRR"] is None:
            return {"EER": None, "threshold": None}
        gap = abs(m["FAR"] - m["FRR"])
        if best is None or gap < best[0]:
            best = (gap, (m["FAR"] + m["FRR"]) / 2, float(t))
    return {"EER": best[1], "threshold": best[2]} if best else {"EER": None, "threshold": None}
