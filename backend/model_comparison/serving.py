"""
Serves the 7 comparison models for live/on-demand prediction against
uploaded tickets — separate from compare.py, which evaluates them via
cross-validation for the static benchmark table.

Models are trained ONCE (on the full training dataset, tickets_10000.ndjson)
and cached in memory, so an upload doesn't retrain from scratch every time.
This mirrors pipeline/classifier.py's load-once-at-startup pattern for the
production classifier.
"""

import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

CLASS_NAMES = ["FALSE_POSITIVE", "NEEDS_REVIEW", "TRUE_POSITIVE"]

from model_comparison.features import extract_features_v2
from model_comparison.models import get_models, NO_SAMPLE_WEIGHT_SUPPORT, SAMPLE_WEIGHT_POWER

TRAIN_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tickets_10000.ndjson")

_trained_models: dict | None = None
_label_encoder: LabelEncoder | None = None


def _train_all_models() -> tuple[dict, LabelEncoder]:
    with open(TRAIN_DATA_PATH) as f:
        tickets = [json.loads(line) for line in f if line.strip()]

    X = np.array([extract_features_v2(t) for t in tickets])
    label_enc = LabelEncoder()
    y = label_enc.fit_transform([t["label"] for t in tickets])

    trained = {}
    for name, (model, _needs_scaling) in get_models().items():
        fit_kwargs = {}
        if name not in NO_SAMPLE_WEIGHT_SUPPORT:
            full_balance = compute_sample_weight("balanced", y)
            sw = 1.0 + SAMPLE_WEIGHT_POWER * (full_balance - 1.0)
            fit_kwargs["clf__sample_weight" if isinstance(model, Pipeline) else "sample_weight"] = sw
        model.fit(X, y, **fit_kwargs)
        trained[name] = model

    return trained, label_enc


def get_trained_models() -> tuple[dict, LabelEncoder]:
    """Lazily trains all 7 models once, then returns the cached copies."""
    global _trained_models, _label_encoder
    if _trained_models is None:
        _trained_models, _label_encoder = _train_all_models()
    return _trained_models, _label_encoder


def predict_all_models(tickets_df: pd.DataFrame) -> dict:
    """
    Runs every uploaded ticket through all 7 trained models.

    Returns a dict with per-ticket predictions from every model, an
    agreement summary, and — if the uploaded file included a `label`
    column — per-model accuracy against those labels.
    """
    models, label_enc = get_trained_models()

    has_labels = "label" in tickets_df.columns
    feature_cols_df = tickets_df.drop(columns=["label"]) if has_labels else tickets_df

    X = np.array([extract_features_v2(t) for t in feature_cols_df.to_dict("records")])

    predictions: dict[str, list[str]] = {}
    for name, model in models.items():
        pred = np.asarray(model.predict(X)).ravel()
        predictions[name] = label_enc.inverse_transform(pred).tolist()

    model_names = list(models.keys())
    tickets = []
    unanimous_count = 0
    for i, ticket_id in enumerate(tickets_df["ticket_id"].tolist()):
        row_predictions = {name: predictions[name][i] for name in model_names}
        distinct_verdicts = set(row_predictions.values())
        is_unanimous = len(distinct_verdicts) == 1
        if is_unanimous:
            unanimous_count += 1

        entry = {
            "ticket_id": ticket_id,
            "predictions": row_predictions,
            "unanimous": is_unanimous,
        }
        if has_labels:
            entry["true_label"] = tickets_df["label"].iloc[i]
        tickets.append(entry)

    result = {
        "has_labels": has_labels,
        "total_tickets": len(tickets),
        "unanimous_count": unanimous_count,
        "unanimous_rate": unanimous_count / len(tickets) if tickets else 0,
        "tickets": tickets,
    }

    if has_labels:
        true_labels = tickets_df["label"].tolist()
        accuracy_per_model = {}
        for name in model_names:
            model_preds = predictions[name]
            correct = sum(1 for p, t in zip(model_preds, true_labels) if p == t)

            precision, recall, f1, _ = precision_recall_fscore_support(
                true_labels, model_preds, labels=CLASS_NAMES, average=None, zero_division=0
            )
            f1_per_class = {cls: float(f1[i]) for i, cls in enumerate(CLASS_NAMES)}
            f1_macro = float(np.mean(f1))

            accuracy_per_model[name] = {
                "correct": correct,
                "total": len(tickets),
                "accuracy": correct / len(tickets),
                "f1_macro": f1_macro,
                "f1_per_class": f1_per_class,
            }
        result["accuracy_per_model"] = accuracy_per_model

    return result
