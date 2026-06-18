"""
One-time XGBoost training script.
Run from the backend/ directory:
    python scripts/train_model.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score

from data.mock_tickets import MOCK_TICKETS, LABEL_MAP
from pipeline.classifier import extract_features_from_dict, FEATURE_NAMES


def main():
    print("=" * 60)
    print("SOC Triage — XGBoost Classifier Training")
    print("=" * 60)

    X = np.array([extract_features_from_dict(t) for t in MOCK_TICKETS])
    y = np.array([LABEL_MAP[t["label"]] for t in MOCK_TICKETS])

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

    # Cross-validation (leave-one-out for small dataset)
    from sklearn.model_selection import LeaveOneOut
    loo = LeaveOneOut()
    scores = cross_val_score(model, X, y, cv=loo, scoring="accuracy")
    print(f"\nLeave-One-Out CV accuracy: {scores.mean():.2%} ± {scores.std():.2%}")

    # Train on full dataset
    model.fit(X, y)

    os.makedirs("models", exist_ok=True)
    model_path = os.getenv("MODEL_PATH", "./models/xgboost_classifier.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")
    print("\nTraining complete.")


if __name__ == "__main__":
    main()
