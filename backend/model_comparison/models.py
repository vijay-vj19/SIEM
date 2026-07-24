"""
Registry of the 7 models being compared for SOC L1 triage classification.

Fairness rules followed here (see conversation context):
  - Every model gets one reasonable, untuned hyperparameter configuration —
    none is hand-tuned or hyperparameter-swept to win. XGBoost previously
    had special-cased hyperparameters and tuning; that has been reverted so
    all 7 are treated identically.
  - Every model that supports sample weighting receives the SAME partial
    class-balanced sample weights (see SAMPLE_WEIGHT_POWER below), applied
    identically in compare.py — not just XGBoost.
  - The one exception is KNN: KNeighborsClassifier.fit() has no
    sample_weight parameter at all (it's instance-based, not a weighted
    training procedure) — this is a scikit-learn library limitation, not a
    choice to exclude it from fair treatment. compare.py skips weighting
    for KNN and this is disclosed alongside the results.
  - Distance/gradient-sensitive models (Logistic Regression, SVM, KNN) are
    wrapped in a Pipeline with StandardScaler. Without scaling, these would
    be unfairly crippled by the features' very different scales (e.g.
    hour_of_day 0-23 vs historical_fp_count 0-60) — that would not be a
    fair comparison, it would just be a scaling bug.
  - Tree models do NOT need scaling (split thresholds are scale-invariant),
    so they are left unscaled.
"""

from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

RANDOM_STATE = 42

# Applied identically to every model below via compute_sample_weight in
# compare.py, except KNN (see module docstring). 0 = no weighting,
# 1 = full inverse-frequency balance. This is now a single shared constant,
# not a model-specific tuning knob.
SAMPLE_WEIGHT_POWER = 0.3

# Models whose underlying estimator's .fit() does NOT accept sample_weight
# at all — compare.py skips weighting for these and discloses it.
NO_SAMPLE_WEIGHT_SUPPORT = {"KNN"}


def get_models() -> dict:
    """Returns {name: (estimator, needs_scaling: bool)}."""
    return {
        "XGBoost": (
            XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                eval_metric="mlogloss",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            False,
        ),
        "CatBoost": (
            CatBoostClassifier(
                iterations=100,
                depth=4,
                learning_rate=0.1,
                random_state=RANDOM_STATE,
                verbose=False,
            ),
            False,
        ),
        "LightGBM": (
            LGBMClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbose=-1,
            ),
            False,
        ),
        "Random Forest": (
            RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
            False,
        ),
        "Logistic Regression": (
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
            ]),
            True,
        ),
        "SVM (RBF)": (
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", SVC(kernel="rbf", probability=True, random_state=RANDOM_STATE)),
            ]),
            True,
        ),
        "KNN": (
            Pipeline([
                ("scaler", StandardScaler()),
                ("clf", KNeighborsClassifier(n_neighbors=15)),
            ]),
            True,
        ),
    }
