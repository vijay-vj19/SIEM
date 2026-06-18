"""
SIR (Security Incident Report) generator.
Uses the original (pre-Presidio) ticket values so analysts see real data.
"""

from datetime import datetime, timezone
from typing import Any


MITRE_DESCRIPTIONS = {
    "T1059": "Command and Scripting Interpreter",
    "T1059.001": "Command and Scripting Interpreter: PowerShell",
    "T1059.003": "Command and Scripting Interpreter: Windows Command Shell",
    "T1003": "OS Credential Dumping",
    "T1003.001": "OS Credential Dumping: LSASS Memory",
    "T1053": "Scheduled Task/Job",
    "T1053.005": "Scheduled Task/Job: Scheduled Task",
    "T1047": "Windows Management Instrumentation",
    "T1078": "Valid Accounts",
    "T1086": "PowerShell (legacy)",
    "T1486": "Data Encrypted for Impact (Ransomware)",
    "T1048": "Exfiltration Over Alternative Protocol",
    "T1048.003": "Exfiltration Over Alternative Protocol: DNS",
    "T1087": "Account Discovery",
    "T1087.001": "Account Discovery: Local Account",
}

VERDICT_ACTIONS = {
    "FALSE_POSITIVE": "[AUTO-CLOSE] This ticket has been automatically classified as a false positive with high confidence. No analyst action required.",
    "TRUE_POSITIVE": "[ESCALATE — P1] Confirmed true positive. Immediately escalate to Tier-2 SOC. Contain the affected asset and begin incident response procedures.",
    "NEEDS_REVIEW": "[ANALYST REVIEW REQUIRED] Confidence is insufficient for automated resolution. A Tier-1 analyst must review this ticket within 4 hours.",
}


def generate_sir(
    ticket: dict[str, Any],
    llm_result: dict[str, Any],
    ml_result: dict[str, Any],
    similar_incidents: list[dict[str, Any]],
    guardrail_status: dict[str, str],
) -> str:
    """
    Build a markdown Security Incident Report.

    Parameters
    ----------
    ticket          : original (non-anonymised) ticket dict
    llm_result      : {verdict, confidence, risk_score, reasoning}
    ml_result       : {verdict, confidence, xgboost_score}
    similar_incidents : list of {ticket_id, similarity, verdict}
    guardrail_status  : {presidio_pii_scan, nemo_input_rail, nemo_output_rail}
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verdict = llm_result.get("verdict", "NEEDS_REVIEW")
    confidence = llm_result.get("confidence", 0.5)
    risk_score = llm_result.get("risk_score", 50)
    reasoning = llm_result.get("reasoning", "No reasoning available.")

    mitre_code = ticket.get("mitre_attack", "N/A")
    mitre_desc = MITRE_DESCRIPTIONS.get(mitre_code, "Unknown Technique")

    ml_verdict = ml_result.get("verdict", "UNKNOWN")
    ml_conf = ml_result.get("xgboost_score", ml_result.get("confidence", 0.5))

    # --- XGBoost feature highlights ---
    user_type = ticket.get("user_type", "")
    hist_fp = ticket.get("historical_fp_count", 0)
    hist_tp = ticket.get("historical_tp_count", 0)
    feature_summary = (
        f"user_type={user_type}, "
        f"historical_fp_count={hist_fp}, "
        f"historical_tp_count={hist_tp}, "
        f"severity={ticket.get('severity', 'N/A')}, "
        f"hour_of_day={ticket.get('hour_of_day', 'N/A')}"
    )

    # --- Similar incidents table ---
    if similar_incidents:
        sim_rows = "\n".join(
            f"| {inc['ticket_id']} | {inc['verdict']} | {inc['similarity']:.0%} |"
            for inc in similar_incidents
        )
        sim_table = (
            "| Ticket       | Verdict        | Similarity |\n"
            "|--------------|----------------|------------|\n"
            f"{sim_rows}"
        )
    else:
        sim_table = "_No similar past incidents found._"

    # --- Guardrail status ---
    gs = guardrail_status
    pii_status = gs.get("presidio_pii_scan", "UNKNOWN")
    nemo_in = gs.get("nemo_input_rail", "UNKNOWN")
    nemo_out = gs.get("nemo_output_rail", "UNKNOWN")

    recommended_action = VERDICT_ACTIONS.get(verdict, VERDICT_ACTIONS["NEEDS_REVIEW"])
    verdict_display = verdict.replace("_", " ")

    report = f"""## Security Incident Report

| Field        | Value                          |
|--------------|--------------------------------|
| Ticket ID    | {ticket.get('ticket_id', 'N/A')} |
| Generated    | {generated_at}                 |
| Verdict      | {verdict_display}              |
| Risk Score   | {risk_score} / 100             |
| Confidence   | {confidence:.0%}               |

### Alert Summary
**{ticket.get('rule_triggered', 'Unknown Rule')}** triggered on \
**{ticket.get('source_asset', 'N/A')}** by user **{ticket.get('user', 'N/A')}** \
at {ticket.get('hour_of_day', 'N/A')}:00 on {ticket.get('day_of_week', 'N/A')}.

- Source IP: `{ticket.get('source_ip', 'N/A')}`
- Target Asset: `{ticket.get('target_asset', 'N/A')}` (`{ticket.get('target_ip', 'N/A')}`)
- Process: `{ticket.get('process', 'N/A')}`
- Command Line:
```
{ticket.get('command_line', 'N/A')}
```
- Decoded Command:
```
{ticket.get('decoded_command', 'N/A')}
```

### MITRE ATT&CK
**Technique:** `{mitre_code}`
**Description:** {mitre_desc}

### ML Analysis
XGBoost classifier: **{ml_verdict}** ({ml_conf:.0%} confidence)
Key features: {feature_summary}

### LLM Reasoning
{reasoning}

### Similar Past Incidents
{sim_table}

### Recommended Action
{recommended_action}

### Guardrail Status
- Presidio PII scan: **{pii_status}**
- NeMo input rail: **{nemo_in}**
- NeMo output rail: **{nemo_out}**
"""
    return report.strip()
