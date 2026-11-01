"""
Generates a SYNTHETIC training dataset for the fraud-risk model.

No real KYC/fraud data exists that a student can legally obtain, so we
simulate plausible combinations of the seven upstream signals and
assign a label using a documented rule (not a black box) that mimics
how a real fraud case *should* look: multiple simultaneous weak
signals => fraud; a single weak signal with everything else strong
=> mostly legitimate, matching how real identity fraud tends to show
up as a *pattern* rather than one isolated red flag.

THIS DATA IS NOT REAL. Any accuracy numbers produced by training on it
describe how well the model learned this synthetic rule, not
real-world fraud-detection performance. This must be stated in any
report or presentation that cites these numbers.

Usage:
    python generate_synthetic_data.py --n 5000 --out synthetic_risk_data.csv
"""
import argparse

import numpy as np
import pandas as pd


def generate(n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    document_authenticity_score = np.clip(rng.normal(85, 15, n), 0, 100)
    tampering_probability = np.clip(rng.beta(1.5, 6, n), 0, 1)
    face_similarity = np.clip(rng.normal(0.8, 0.15, n), 0, 1)
    face_quality = np.clip(rng.normal(0.75, 0.15, n), 0, 1)
    liveness_passed = rng.random(n) > 0.15
    deepfake_probability = np.clip(rng.beta(1.5, 6, n), 0, 1)
    replay_probability = np.clip(rng.beta(1.5, 6, n), 0, 1)

    # Weak-signal count -> fraud likelihood (documented rule, not hidden)
    weak_signals = (
        (document_authenticity_score < 60).astype(int)
        + (tampering_probability > 0.5).astype(int)
        + (face_similarity < 0.55).astype(int)
        + (face_quality < 0.4).astype(int)
        + (~liveness_passed).astype(int)
        + (deepfake_probability > 0.5).astype(int)
        + (replay_probability > 0.5).astype(int)
    )
    fraud_prob = np.clip(0.03 + 0.16 * weak_signals, 0, 0.97)
    label = (rng.random(n) < fraud_prob).astype(int)

    # rPPG (added for model v2). ASSUMPTION encoded here, stated openly: in
    # this synthetic world, genuine live sessions more often yield a usable
    # pulse signal with a healthier score, while presentation attacks more
    # often yield none or a weak one. A reading is MISSING (NaN) when the
    # signal is insufficient/unavailable -- the real pipeline reports that
    # case as INSUFFICIENT_SIGNAL/UNAVAILABLE and never invents a value.
    # Deliberately a WEAK, heavily overlapping signal (rPPG is noisy and is
    # never a stand-alone detector): attack mean ~0.45 vs genuine ~0.58,
    # with wide spread, so it nudges the score rather than deciding it.
    available = np.where(label == 1, rng.random(n) < 0.60, rng.random(n) < 0.72)
    rppg_raw = np.where(label == 1, rng.beta(3.2, 3.9, n), rng.beta(4.0, 3.0, n))
    rppg_score = np.where(available, rppg_raw * 100, np.nan)

    df = pd.DataFrame(
        {
            "document_authenticity_score": document_authenticity_score,
            "tampering_probability": tampering_probability * 100,
            "face_similarity": face_similarity * 100,
            "face_quality": face_quality * 100,
            "liveness_passed": liveness_passed.astype(int) * 100,
            "deepfake_probability": deepfake_probability * 100,
            "replay_probability": replay_probability * 100,
            "rppg_score": rppg_score,
            "label": label,
        }
    )
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5000)
    parser.add_argument("--out", type=str, default="synthetic_risk_data.csv")
    args = parser.parse_args()

    df = generate(args.n)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic rows to {args.out}")
    print(f"Fraud label rate: {df['label'].mean():.3f}")
