"""
Generates a genuinely INDEPENDENT validation dataset — same templates and
label-generation rules as generate_tickets_v2.py, but a different random
seed, so these tickets were never part of the data the 7 models trained on
(unlike tickets_10000.ndjson's 90/10 CV holdout, which is a slice of the same
generation run as training).

Produces two paired Excel files for manual upload-and-check testing:
  - validation_set_labeled.xlsx   (includes the true `label` column — answer key)
  - validation_set_unlabeled.xlsx (same rows, `label` column removed — for upload)

Run (from backend/):
    python -m model_comparison.generate_validation_set
"""

import json
import os
import random

import pandas as pd

# Reuse all the templates / logic from generate_tickets_v2, just with a
# different seed and row count — this is intentionally a SEPARATE script
# from generate_tickets_v2.py's own CLI so the training dataset is never
# touched by running this.
import model_comparison.generate_tickets_v2 as gen

VALIDATION_ROWS = 4500
VALIDATION_SEED = 99  # different from generate_tickets_v2.py's seed (7)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NDJSON_PATH = os.path.join(OUT_DIR, "validation_set.ndjson")
LABELED_XLSX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "validation_set_labeled.xlsx")
UNLABELED_XLSX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "validation_set_unlabeled.xlsx")


def main():
    print("=" * 70)
    print("Independent Validation Set Generator")
    print("=" * 70)

    random.seed(VALIDATION_SEED)
    tickets = gen.generate(VALIDATION_ROWS)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(NDJSON_PATH, "w") as f:
        for t in tickets:
            f.write(json.dumps(t) + "\n")
    print(f"\nWrote {len(tickets)} tickets to {NDJSON_PATH}")

    total = len(tickets)
    print("\nLabel distribution:")
    for label in gen.LABELS:
        count = sum(1 for t in tickets if t["label"] == label)
        print(f"  {label:20s}: {count:5d}  ({count / total:.1%})")

    print("\nSanity check (rule_triggered-only baseline, 5-fold CV)...")
    baseline_acc = gen._rule_only_baseline_check(tickets)
    print(f"  rule_triggered-only accuracy: {baseline_acc:.2%}")
    if baseline_acc >= 0.95:
        print("  WARNING: rule_triggered alone is a near-perfect predictor here.")
    else:
        print("  OK: not a near-perfect predictor.")

    df = pd.DataFrame(tickets)
    df.to_excel(os.path.abspath(LABELED_XLSX), index=False)
    print(f"\nLabeled file (answer key) written to {os.path.abspath(LABELED_XLSX)}")

    input_cols = [c for c in df.columns if c != "label"]
    df[input_cols].to_excel(os.path.abspath(UNLABELED_XLSX), index=False)
    print(f"Unlabeled file (for upload) written to {os.path.abspath(UNLABELED_XLSX)}")


if __name__ == "__main__":
    main()
