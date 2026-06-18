"""
One-time XGBoost training script.
Run from the backend/ directory:
    python scripts/train_model.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

import joblib
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold

from data.mock_tickets import LABEL_MAP
from pipeline.classifier import extract_features_from_dict, FEATURE_NAMES

TICKETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets_100.ndjson")


def load_tickets() -> list[dict]:
    with open(TICKETS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    print("=" * 60)
    print("SOC Triage — XGBoost Classifier Training")
    print("=" * 60)

    tickets = load_tickets()
    X = np.array([extract_features_from_dict(t) for t in tickets])
    y = np.array([LABEL_MAP[t["label"]] for t in tickets])

    print(f"\nTraining samples : {len(X)}")
    print(f"Feature names    : {FEATURE_NAMES}")
    print(f"Label distribution:")
    for label, idx in LABEL_MAP.items():
        count = (y == idx).sum()
        print(f"  {label:20s}: {count}")

    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

    # 5-fold stratified cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"\n5-Fold CV accuracy: {scores.mean():.2%} ± {scores.std():.2%}")

    # Train on full dataset
    model.fit(X, y)

    os.makedirs("models", exist_ok=True)
    model_path = os.getenv("MODEL_PATH", "./models/xgboost_classifier.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")
    print("\nTraining complete.")


if __name__ == "__main__":
    main()
