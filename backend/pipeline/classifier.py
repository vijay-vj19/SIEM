"""
XGBoost classifier: feature engineering + prediction.
Model is loaded once at app startup via load_model().
"""

import logging
import os
from typing import Any

import joblib
import numpy as np

from models.ticket import TicketIn
from data.mock_tickets import LABEL_NAMES

logger = logging.getLogger(__name__)

_model = None

# ---------------------------------------------------------------------------
# Feature engineering constants
# ---------------------------------------------------------------------------
SEVERITY_MAP = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
USER_TYPE_MAP = {"service_account": 0, "standard_user": 1, "admin_user": 2}
DAY_MAP = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}

MITRE_MAP = {
    "T1059": 1, "T1059.001": 1, "T1059.003": 1,
    "T1003": 2, "T1003.001": 2,
    "T1053": 3, "T1053.005": 3,
    "T1047": 4,
    "T1078": 5,
    "T1486": 6,
    "T1048": 7, "T1048.003": 7,
    "T1087": 8, "T1087.001": 8,
}

KNOWN_MALICIOUS_TOOLS = {
    "mimikatz", "cobalt", "meterpreter", "empire", "bloodhound",
    "sharphound", "rubeus", "kerbrute", "crackmapexec", "impacket",
    "psexec", "ncrack", "hydra", "responder",
}

INTERNAL_RANGES = ("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                   "172.20.", "192.168.", "127.")


def _is_external_ip(ip: str) -> int:
    return 0 if any(ip.startswith(r) for r in INTERNAL_RANGES) else 1


def _is_known_tool(process: str, command_line: str) -> int:
    combined = (process + " " + command_line).lower()
    return int(any(tool in combined for tool in KNOWN_MALICIOUS_TOOLS))


def _target_is_dc(target_asset: str, target_ip: str) -> int:
    asset_lower = target_asset.lower()
    return int("dc-" in asset_lower or "dc0" in asset_lower or "domain-controller" in asset_lower)


def extract_features(ticket: TicketIn) -> np.ndarray:
    """Convert a TicketIn into a 1-D numpy feature vector."""
    mitre_key = ticket.mitre_attack.strip()
    mitre_encoded = MITRE_MAP.get(mitre_key, 0)

    features = [
        SEVERITY_MAP.get(ticket.severity.value if hasattr(ticket.severity, "value") else ticket.severity, 2),
        USER_TYPE_MAP.get(ticket.user_type.value if hasattr(ticket.user_type, "value") else ticket.user_type, 1),
        ticket.hour_of_day,
        1 if DAY_MAP.get(ticket.day_of_week, 0) >= 5 else 0,
        ticket.historical_tp_count,
        ticket.historical_fp_count,
        mitre_encoded,
        _is_external_ip(ticket.target_ip),
        _is_known_tool(ticket.process, ticket.command_line),
        _target_is_dc(ticket.target_asset, ticket.target_ip),
    ]
    return np.array(features, dtype=float).reshape(1, -1)


def extract_features_from_dict(t: dict) -> np.ndarray:
    """Feature extraction from a raw dict (used during training)."""
    mitre_encoded = MITRE_MAP.get(t.get("mitre_attack", ""), 0)
    severity_val = t.get("severity", "MEDIUM")
    user_type_val = t.get("user_type", "standard_user")

    features = [
        SEVERITY_MAP.get(severity_val, 2),
        USER_TYPE_MAP.get(user_type_val, 1),
        int(t.get("hour_of_day", 12)),
        1 if DAY_MAP.get(t.get("day_of_week", "Monday"), 0) >= 5 else 0,
        int(t.get("historical_tp_count", 0)),
        int(t.get("historical_fp_count", 0)),
        mitre_encoded,
        _is_external_ip(t.get("target_ip", "10.0.0.1")),
        _is_known_tool(t.get("process", ""), t.get("command_line", "")),
        _target_is_dc(t.get("target_asset", ""), t.get("target_ip", "")),
    ]
    return np.array(features, dtype=float)


FEATURE_NAMES = [
    "severity_encoded",
    "user_type_encoded",
    "hour_of_day",
    "is_weekend",
    "historical_tp_count",
    "historical_fp_count",
    "mitre_tactic_encoded",
    "is_external_ip",
    "is_known_tool",
    "target_is_dc",
]


# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------

def load_model(path: str | None = None) -> None:
    global _model
    model_path = path or os.getenv("MODEL_PATH", "./models/xgboost_classifier.pkl")
    try:
        _model = joblib.load(model_path)
        logger.info(f"XGBoost model loaded from {model_path}")
    except FileNotFoundError:
        logger.error(
            f"Model not found at {model_path}. "
            "Run: python scripts/train_model.py"
        )
        _model = None


def predict(ticket: TicketIn) -> dict[str, Any]:
    """
    Run XGBoost prediction on a single ticket.
    Returns dict with verdict (label string) and confidence (float).
    """
    if _model is None:
        logger.warning("XGBoost model not loaded — returning NEEDS_REVIEW fallback")
        return {"verdict": "NEEDS_REVIEW", "confidence": 0.5, "xgboost_score": 0.5}

    features = extract_features(ticket)
    proba = _model.predict_proba(features)[0]
    class_idx = int(proba.argmax())
    confidence = float(proba[class_idx])
    verdict = LABEL_NAMES.get(class_idx, "NEEDS_REVIEW")

    return {
        "verdict": verdict,
        "confidence": round(confidence, 4),
        "xgboost_score": round(confidence, 4),
    }
