"""
7-model comparison harness for the SOC L1 triage classifier.

Runs identical 5-fold stratified CV for all 7 models on the same dataset
(tickets_10000.ndjson) with the same 17 engineered features, then reports
accuracy, macro precision/recall/F1, confusion matrix, train time,
per-ticket inference time, and on-disk model size for each.

Run (from backend/):
    python -m model_comparison.compare
Output:
    Printed comparison table + model_comparison/data/comparison_results.json
"""

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from model_comparison.features import extract_features_v2, FEATURE_NAMES_V2
from model_comparison.models import get_models, RANDOM_STATE, SAMPLE_WEIGHT_POWER, NO_SAMPLE_WEIGHT_SUPPORT

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tickets_10000.ndjson")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "comparison_results.json")
N_SPLITS = 5


def load_dataset():
    with open(DATA_PATH) as f:
        tickets = [json.loads(line) for line in f if line.strip()]

    X = np.array([extract_features_v2(t) for t in tickets])
    label_enc = LabelEncoder()
    y = label_enc.fit_transform([t["label"] for t in tickets])
    return X, y, label_enc


def _model_size_bytes(model) -> int:
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        joblib.dump(model, tmp.name)
        size = os.path.getsize(tmp.name)
    os.unlink(tmp.name)
    return size


def evaluate_model(name: str, model, X: np.ndarray, y: np.ndarray, label_enc: LabelEncoder) -> dict:
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    fold_accuracies = []
    all_y_true, all_y_pred = [], []
    fold_train_times, fold_inference_times_per_ticket = [], []

    for train_idx, test_idx in cv.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        fold_model = _clone(model)

        # Same partial class-balanced sample weighting applied to EVERY
        # model, uniformly — not just one. The only exception is KNN, whose
        # underlying estimator has no sample_weight parameter at all (a
        # scikit-learn library limitation: KNN is instance-based, there is
        # no weighted training step to apply weights to), listed in
        # NO_SAMPLE_WEIGHT_SUPPORT and disclosed in the output below.
        fit_kwargs = {}
        if name not in NO_SAMPLE_WEIGHT_SUPPORT:
            full_balance = compute_sample_weight("balanced", y_train)
            sample_weight = 1.0 + SAMPLE_WEIGHT_POWER * (full_balance - 1.0)
            # Pipeline-wrapped models (Logistic Regression, SVM) need the
            # weight routed to the "clf" step specifically.
            if isinstance(fold_model, Pipeline):
                fit_kwargs["clf__sample_weight"] = sample_weight
            else:
                fit_kwargs["sample_weight"] = sample_weight

        t0 = time.perf_counter()
        fold_model.fit(X_train, y_train, **fit_kwargs)
        train_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        y_pred = fold_model.predict(X_test)
        total_inference_time = time.perf_counter() - t0
        per_ticket_ms = (total_inference_time / len(X_test)) * 1000

        # CatBoost's predict() returns shape (n, 1) instead of flat (n,) like
        # every other library here. Without ravel(), (y_pred == y_test) would
        # broadcast to an (n, n) matrix instead of comparing elementwise,
        # silently producing a meaningless accuracy number for CatBoost only.
        y_pred = np.asarray(y_pred).ravel()

        fold_accuracies.append((y_pred == y_test).mean())
        all_y_true.extend(y_test.tolist())
        all_y_pred.extend(y_pred.tolist())
        fold_train_times.append(train_time)
        fold_inference_times_per_ticket.append(per_ticket_ms)

    precision, recall, f1, _ = precision_recall_fscore_support(
        all_y_true, all_y_pred, average="macro", zero_division=0
    )
    cm = confusion_matrix(all_y_true, all_y_pred).tolist()

    # Fit once more on the full dataset to measure realistic on-disk size
    full_model = _clone(model)
    full_model.fit(X, y)
    size_bytes = _model_size_bytes(full_model)

    return {
        "name": name,
        "accuracy_mean": float(np.mean(fold_accuracies)),
        "accuracy_std": float(np.std(fold_accuracies)),
        "precision_macro": float(precision),
        "recall_macro": float(recall),
        "f1_macro": float(f1),
        "confusion_matrix": cm,
        "confusion_matrix_labels": label_enc.classes_.tolist(),
        "train_time_sec_mean": float(np.mean(fold_train_times)),
        "inference_ms_per_ticket_mean": float(np.mean(fold_inference_times_per_ticket)),
        "model_size_kb": round(size_bytes / 1024, 1),
    }


def _clone(model):
    from sklearn.base import clone
    return clone(model)


def main():
    print("=" * 70)
    print("SOC Triage — 7-Model Comparison")
    print("=" * 70)

    print(
        "\nNOTE: All 7 models use one untuned, reasonable hyperparameter "
        "configuration each, and all receive the SAME partial class-balanced "
        "sample weights (power=%.1f), applied identically. The one exception "
        "is KNN, which has no sample_weight support at all in scikit-learn "
        "(a library limitation, not a choice to exclude it)." % SAMPLE_WEIGHT_POWER
    )

    X, y, label_enc = load_dataset()
    print(f"\nDataset: {DATA_PATH}")
    print(f"Rows: {len(X)}  Features: {len(FEATURE_NAMES_V2)}  Classes: {list(label_enc.classes_)}")

    models = get_models()
    results = []

    for name, (model, _needs_scaling) in models.items():
        print(f"\nEvaluating {name}...")
        result = evaluate_model(name, model, X, y, label_enc)
        results.append(result)
        print(
            f"  accuracy={result['accuracy_mean']:.2%} (+/- {result['accuracy_std']:.2%})  "
            f"f1_macro={result['f1_macro']:.3f}  "
            f"train={result['train_time_sec_mean']*1000:.1f}ms  "
            f"infer={result['inference_ms_per_ticket_mean']:.3f}ms/ticket  "
            f"size={result['model_size_kb']}KB"
        )

    results.sort(key=lambda r: r["accuracy_mean"], reverse=True)

    print("\n" + "=" * 70)
    print("SUMMARY (sorted by accuracy)")
    print("=" * 70)
    header = f"{'Model':<22}{'Accuracy':<12}{'F1(macro)':<12}{'Train(ms)':<12}{'Infer(ms)':<12}{'Size(KB)':<10}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['name']:<22}"
            + f"{r['accuracy_mean']:.2%}".ljust(12)
            + f"{r['f1_macro']:.3f}".ljust(12)
            + f"{r['train_time_sec_mean']*1000:.1f}".ljust(12)
            + f"{r['inference_ms_per_ticket_mean']:.3f}".ljust(12)
            + f"{r['model_size_kb']}".ljust(10)
        )

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump({
            "dataset_rows": len(X),
            "n_splits": N_SPLITS,
            "disclosure": (
                f"All 7 models use one untuned, reasonable hyperparameter configuration "
                f"each, and all receive identical partial class-balanced sample weights "
                f"(power={SAMPLE_WEIGHT_POWER}). Exception: KNN has no sample_weight "
                f"support in scikit-learn (library limitation, not exclusion by choice)."
            ),
            "results": results,
        }, f, indent=2)
    print(f"\nFull results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
