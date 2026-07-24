"""
Intuitive spot-check: hold back a slice of tickets none of the 7 models ever
trained on, then show the TRUE label next to what each model actually
predicted for that specific ticket — side by side, one row per ticket.

This is a more tangible way to see "32.5% NEEDS_REVIEW recall" than reading
an aggregate number: you can see exactly which specific ambiguous tickets
XGBoost caught that Random Forest missed, and vice versa.

Run (from backend/):
    python -m model_comparison.spot_check
Output:
    Printed table (focused on NEEDS_REVIEW tickets) +
    model_comparison/data/spot_check.xlsx (full held-out set, all columns)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from model_comparison.features import extract_features_v2
from model_comparison.models import get_models, RANDOM_STATE, SAMPLE_WEIGHT_POWER, NO_SAMPLE_WEIGHT_SUPPORT

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tickets_10000.ndjson")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "spot_check.xlsx")
HOLDOUT_FRACTION = 0.1  # ~400 tickets never seen during training


def main():
    with open(DATA_PATH) as f:
        tickets = [json.loads(line) for line in f if line.strip()]

    X = np.array([extract_features_v2(t) for t in tickets])
    label_enc = LabelEncoder()
    y = label_enc.fit_transform([t["label"] for t in tickets])
    ticket_ids = [t["ticket_id"] for t in tickets]

    idx = np.arange(len(tickets))
    train_idx, holdout_idx = train_test_split(
        idx, test_size=HOLDOUT_FRACTION, stratify=y, random_state=RANDOM_STATE
    )
    X_train, y_train = X[train_idx], y[train_idx]
    X_holdout, y_holdout = X[holdout_idx], y[holdout_idx]
    holdout_ticket_ids = [ticket_ids[i] for i in holdout_idx]

    print(f"Training on {len(train_idx)} tickets, holding out {len(holdout_idx)} never-seen tickets.\n")

    predictions = {"ticket_id": holdout_ticket_ids, "true_label": label_enc.inverse_transform(y_holdout)}

    for name, (model, _needs_scaling) in get_models().items():
        fit_kwargs = {}
        if name not in NO_SAMPLE_WEIGHT_SUPPORT:
            full_balance = compute_sample_weight("balanced", y_train)
            sw = 1.0 + SAMPLE_WEIGHT_POWER * (full_balance - 1.0)
            fit_kwargs["clf__sample_weight" if isinstance(model, Pipeline) else "sample_weight"] = sw

        model.fit(X_train, y_train, **fit_kwargs)
        pred = np.asarray(model.predict(X_holdout)).ravel()
        predictions[name] = label_enc.inverse_transform(pred)

    df = pd.DataFrame(predictions)
    df.to_excel(OUT_PATH, index=False)
    print(f"Full held-out spot-check written to {OUT_PATH} ({len(df)} rows)\n")

    # The interesting part: only the tickets that were ACTUALLY NEEDS_REVIEW,
    # showing which models caught it and which didn't.
    nr_only = df[df["true_label"] == "NEEDS_REVIEW"].copy()
    model_names = list(get_models().keys())
    nr_only["models_correct"] = nr_only[model_names].apply(
        lambda row: sum(row[m] == "NEEDS_REVIEW" for m in model_names), axis=1
    )
    nr_only = nr_only.sort_values("models_correct", ascending=False)

    print(f"Held-out tickets that were TRULY NEEDS_REVIEW: {len(nr_only)}")
    print(f"(showing which of the 7 models actually caught each one)\n")
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print(nr_only.head(20).to_string(index=False))

    print(f"\nModels-correct distribution across all {len(nr_only)} true NEEDS_REVIEW holdout tickets:")
    print(nr_only["models_correct"].value_counts().sort_index(ascending=False).to_string())


if __name__ == "__main__":
    main()
