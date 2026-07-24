"""
Extended feature set for the 7-model comparison ONLY — does not touch
production's pipeline/classifier.py or its 10-feature contract.

Why this exists: with only the original 10 features, all 7 models converge
to roughly the same accuracy (62-65%), because there isn't enough feature
complexity for any model's inductive bias (tree-split vs. linear vs. kernel
vs. distance) to meaningfully differ. This adds:
  - text-derived signals from command_line/decoded_command (length, entropy,
    obfuscation keywords, scripting-process flag) — real signal that exists
    in the data but the original 10 features never captured
  - a broader MITRE tactic bucket (beyond the existing per-technique-only
    MITRE_MAP), giving a coarser but genuinely informative category
  - two explicit interaction terms (known_tool x target_is_dc,
    severity x external_ip) — the kind of non-additive structure tree
    ensembles can exploit natively but a plain linear model cannot, which is
    where real separation between model families should start to appear

All features are computed purely from ticket fields already present in the
schema — no label leakage, no data-dependent (fold-varying) statistics.
"""

import math
import re

from pipeline.classifier import (
    DAY_MAP,
    MITRE_MAP,
    SEVERITY_MAP,
    USER_TYPE_MAP,
    _is_external_ip,
    _is_known_tool,
    _target_is_dc,
)

SCRIPTING_PROCESSES = {"powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe", "mshta.exe", "rundll32.exe"}

OBFUSCATION_KEYWORDS = (
    "-enc", "-e ", "encodedcommand", "-nop", "bypass", "hidden",
    "downloadstring", "iex", "frombase64", "invoke-expression",
)

# Coarse MITRE tactic bucket by technique root (broader than the existing
# per-technique-only MITRE_MAP used in production).
TACTIC_MAP = {
    "T1059": "execution", "T1053": "persistence", "T1047": "execution",
    "T1087": "discovery", "T1078": "defense_evasion", "T1003": "credential_access",
    "T1486": "impact", "T1048": "exfiltration", "T1098": "persistence",
    "T1055": "defense_evasion", "T1071": "command_and_control", "T1136": "persistence",
    "T1547": "persistence", "T1070": "defense_evasion", "T1027": "defense_evasion",
    "T1204": "execution", "T1566": "initial_access", "T1110": "credential_access",
    "T1552": "credential_access", "T1546": "persistence", "T1082": "discovery",
    "T1016": "discovery", "T1069": "discovery", "T1018": "discovery",
    "T1135": "discovery", "T1021": "lateral_movement", "T1560": "collection",
    "T1114": "collection", "T1567": "exfiltration", "T1562": "defense_evasion",
    "T1490": "impact",
}
TACTIC_BUCKETS = sorted(set(TACTIC_MAP.values())) + ["unknown"]
TACTIC_ENCODED = {name: i for i, name in enumerate(TACTIC_BUCKETS)}


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(s)
    return -sum((c / length) * math.log2(c / length) for c in freq.values())


def _has_obfuscation_keyword(command_line: str, decoded_command: str) -> int:
    combined = (command_line + " " + decoded_command).lower()
    return int(any(kw in combined for kw in OBFUSCATION_KEYWORDS))


def _tactic_bucket(mitre_attack: str) -> str:
    root = re.split(r"\.", mitre_attack.strip())[0]
    return TACTIC_MAP.get(root, "unknown")


FEATURE_NAMES_V2 = [
    # original 10 (same as production pipeline/classifier.py)
    "severity_encoded", "user_type_encoded", "hour_of_day", "is_weekend",
    "historical_tp_count", "historical_fp_count", "mitre_tactic_encoded",
    "is_external_ip", "is_known_tool", "target_is_dc",
    # new: text-derived
    "command_line_length", "decoded_command_entropy", "has_obfuscation_keyword",
    "is_scripting_process",
    # new: broader category
    "tactic_bucket_encoded",
    # new: explicit interaction terms
    "known_tool_x_target_dc", "severity_x_external_ip",
]


def extract_features_v2(t: dict):
    import numpy as np

    severity_val = t.get("severity", "MEDIUM")
    user_type_val = t.get("user_type", "standard_user")
    mitre = t.get("mitre_attack", "")
    process = t.get("process", "")
    command_line = t.get("command_line", "") or ""
    decoded_command = t.get("decoded_command", "") or ""
    target_ip = t.get("target_ip", "10.0.0.1")
    target_asset = t.get("target_asset", "")

    severity_encoded = SEVERITY_MAP.get(severity_val, 2)
    mitre_encoded = MITRE_MAP.get(mitre, 0)
    is_external = _is_external_ip(target_ip)
    known_tool = _is_known_tool(process, command_line)
    is_dc = _target_is_dc(target_asset, target_ip)

    base = [
        severity_encoded,
        USER_TYPE_MAP.get(user_type_val, 1),
        int(t.get("hour_of_day", 12)),
        1 if DAY_MAP.get(t.get("day_of_week", "Monday"), 0) >= 5 else 0,
        int(t.get("historical_tp_count", 0)),
        int(t.get("historical_fp_count", 0)),
        mitre_encoded,
        is_external,
        known_tool,
        is_dc,
    ]

    extended = [
        len(command_line),
        _shannon_entropy(decoded_command),
        _has_obfuscation_keyword(command_line, decoded_command),
        int(process.lower() in SCRIPTING_PROCESSES),
        TACTIC_ENCODED[_tactic_bucket(mitre)],
        known_tool * is_dc,
        severity_encoded * is_external,
    ]

    return np.array(base + extended, dtype=float)
