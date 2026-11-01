"""
Trains the fraud-risk model (Model F) on the synthetic dataset produced
by generate_synthetic_data.py, with a proper train/validation/test
split to avoid data leakage, and saves a joblib bundle that
app/ml/risk_engine.py loads at inference time.

Tries XGBoost first (more capacity, native SHAP TreeExplainer support);
falls back to Logistic Regression (fully transparent, coefficients are
directly interpretable) if xgboost isn't installed.

Usage:
    python generate_synthetic_data.py --n 8000 --out synthetic_risk_data.csv
    python train_risk_model.py --data synthetic_risk_data.csv --out ../../backend/storage/models/risk_model.joblib
    python train_risk_model.py --data synthetic_risk_data.csv --with-rppg --out ../../backend/storage/models/risk_model_v2.joblib
"""
import argparse
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

FEATURES = [
    "document_authenticity_score",
    "tampering_probability",
    "face_similarity",
    "face_quality",
    "liveness_passed",
    "deepfake_probability",
    "replay_probability",
]


FEATURES_V2 = FEATURES + ["rppg_score"]


def train(data_path: str, out_path: str, with_rppg: bool = False):
    features = FEATURES_V2 if with_rppg else FEATURES
    df = pd.read_csv(data_path)
    X = df[features]
    y = df["label"]

    # 70/15/15 train/val/test split, stratified to keep fraud-rate balance across splits
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=42)

    if with_rppg:
        # rppg_score has genuine missing values (NaN = no usable pulse
        # signal). XGBoost routes NaN natively; logistic regression can't,
        # so v2 requires xgboost rather than imputing a fake value.
        try:
            import xgboost  # noqa: F401
        except ImportError as exc:
            raise SystemExit("--with-rppg requires xgboost (pip install xgboost)") from exc

    model_kind = "logistic_regression"
    # The synthetic fraud rate is intentionally low (realistic base rate),
    # so we correct for class imbalance rather than letting the model
    # default to always predicting "not fraud".
    scale_pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    try:
        import xgboost as xgb

        params = dict(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=42,
        )
        if with_rppg:
            # v2: rPPG is a noisy, supplementary signal, so use a shallow,
            # regularized model, plus a monotone constraint encoding the
            # domain prior "a stronger physiological signal never INCREASES
            # fraud risk". scale_pos_weight is deliberately NOT used: it
            # inflates probabilities for the rare fraud class, and with a
            # regularized model that made even perfect cases score ~40/100.
            # Without it the output is a calibrated probability under the
            # synthetic base rate (clean case ~3, three weak signals ~70).
            params.pop("scale_pos_weight")
            params.update(
                n_estimators=300, max_depth=3, learning_rate=0.05,
                min_child_weight=5, reg_lambda=5,
                monotone_constraints="(" + ",".join("-1" if f == "rppg_score" else "0" for f in features) + ")",
            )
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        model_kind = "xgboost"
    except ImportError:
        model = LogisticRegression(max_iter=1000, class_weight="balanced")
        model.fit(X_train, y_train)

    def evaluate(split_name, X_split, y_split):
        preds = model.predict(X_split)
        proba = model.predict_proba(X_split)[:, 1]
        print(f"\n--- {split_name} ({len(X_split)} rows) ---")
        print(f"Accuracy:  {accuracy_score(y_split, preds):.4f}")
        print(f"Precision: {precision_score(y_split, preds, zero_division=0):.4f}")
        print(f"Recall:    {recall_score(y_split, preds, zero_division=0):.4f}")
        print(f"F1:        {f1_score(y_split, preds, zero_division=0):.4f}")
        print(f"ROC-AUC:   {roc_auc_score(y_split, proba):.4f}")
        print(f"Confusion matrix:\n{confusion_matrix(y_split, preds)}")
        return {
            "n": int(len(X_split)),
            "accuracy": float(accuracy_score(y_split, preds)),
            "precision": float(precision_score(y_split, preds, zero_division=0)),
            "recall": float(recall_score(y_split, preds, zero_division=0)),
            "f1": float(f1_score(y_split, preds, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_split, proba)),
            "confusion_matrix": confusion_matrix(y_split, preds).tolist(),
        }

    evaluate("VALIDATION", X_val, y_val)
    test_metrics = evaluate("TEST", X_test, y_test)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "model_kind": model_kind,
            "features": features,
            "version": "trained_on_synthetic_data_v2_rppg" if with_rppg else "trained_on_synthetic_data_v1",
            "note": "Trained on SYNTHETIC data only. Metrics above reflect performance on the synthetic "
            "rule described in generate_synthetic_data.py, not real-world fraud detection.",
        },
        out_path,
    )
    import json

    with open(out_path + ".metrics.json", "w") as fh:
        json.dump(
            {
                "dataset": "SYNTHETIC (generate_synthetic_data.py) -- not real fraud data",
                "test": test_metrics,
                "note": "Measures how well the model recovers the documented synthetic rule; NOT real-world fraud-detection performance.",
            },
            fh,
            indent=2,
        )
    print(f"\nSaved model bundle ({model_kind}) to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="synthetic_risk_data.csv")
    parser.add_argument("--out", type=str, default="../../backend/storage/models/risk_model.joblib")
    parser.add_argument("--with-rppg", action="store_true", help="train v2 with rppg_score as an 8th feature (NaN allowed)")
    args = parser.parse_args()
    train(args.data, args.out, with_rppg=args.with_rppg)
