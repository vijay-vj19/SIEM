"""
LLM triage: GPT-4o-mini call for verdict confirmation + reasoning.
Receives anonymised ticket data from the guardrail pipeline.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a SOC Level-1 triage analyst AI. You receive a SIEM security alert \
with structured metadata, an ML classifier verdict with confidence score, \
and similar past incidents retrieved from the knowledge base.

Your job is to:
1. Confirm or override the ML verdict (TRUE_POSITIVE / FALSE_POSITIVE / NEEDS_REVIEW)
2. Explain your reasoning in 2-3 plain English sentences
3. Assign a risk score from 0-100 (0=harmless, 100=critical breach in progress)
4. State the single most likely root cause in one sentence, grounded only in the ticket
   data, ML verdict, and similar incidents provided — never invent details not present
   in the input (no fabricated timelines, names, or forensic findings)
5. List 2-4 short contributing factors that support the root cause (e.g. historical
   FP/TP counts, time of day, account type, similarity to past incidents)
6. Return ONLY valid JSON — no markdown, no explanation outside the JSON

Response format:
{
  "verdict": "FALSE_POSITIVE",
  "confidence": 0.94,
  "risk_score": 8,
  "reasoning": "The account SVC-AnsibleDeploy is a known automation service account with 47 historical false positives on this exact rule. The decoded PowerShell command performs a routine Windows Time service health check with no malicious indicators. This is consistent with standard Ansible deployment automation.",
  "root_cause": "Automated detection rule flagging routine Ansible service-account automation as suspicious PowerShell usage.",
  "contributing_factors": [
    "Service account with 47 historical false positives on this exact rule",
    "Decoded command is a benign Windows Time service health check",
    "No external IP or known malicious tool involved"
  ]
}"""


def _build_user_message(
    safe_ticket: dict,
    ml_verdict: str,
    ml_confidence: float,
    similar_incidents: list[dict],
) -> str:
    ticket_json = json.dumps(safe_ticket, indent=2, default=str)
    incidents_text = (
        json.dumps(similar_incidents, indent=2) if similar_incidents else "None found"
    )
    return (
        f"TICKET:\n{ticket_json}\n\n"
        f"ML VERDICT: {ml_verdict} (confidence: {ml_confidence:.2%})\n\n"
        f"SIMILAR PAST INCIDENTS:\n{incidents_text}"
    )


def run_llm_triage(
    safe_ticket: dict,
    ml_result: dict[str, Any],
    similar_incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Call GPT-4o-mini to confirm/override the XGBoost verdict.
    Returns dict with: verdict, confidence, risk_score, reasoning.
    Falls back gracefully if OpenAI key is not set.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_key_here":
        logger.warning("OPENAI_API_KEY not set — returning ML verdict as LLM verdict")
        return _fallback_from_ml(ml_result)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        user_msg = _build_user_message(
            safe_ticket,
            ml_result["verdict"],
            ml_result["confidence"],
            similar_incidents,
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)

        # Normalise fields
        return {
            "verdict": parsed.get("verdict", ml_result["verdict"]),
            "confidence": _normalise_confidence(parsed.get("confidence", ml_result["confidence"])),
            "risk_score": int(parsed.get("risk_score", 50)),
            "reasoning": parsed.get("reasoning", "No reasoning provided."),
            "root_cause": parsed.get("root_cause", "Not determined from available data."),
            "contributing_factors": parsed.get("contributing_factors", []),
        }

    except json.JSONDecodeError as exc:
        logger.error(f"LLM returned invalid JSON: {exc}")
        return _fallback_from_ml(ml_result, reasoning="LLM returned malformed JSON.")
    except Exception as exc:
        logger.error(f"LLM call failed: {exc}")
        return _fallback_from_ml(ml_result, reasoning=f"LLM unavailable: {exc}")


def _normalise_confidence(value: float) -> float:
    """LLM sometimes returns confidence as a percentage (e.g. 55) instead of a 0-1 fraction."""
    value = float(value)
    if value > 1:
        value /= 100
    return max(0.0, min(1.0, round(value, 4)))


def _fallback_from_ml(ml_result: dict, reasoning: str = "") -> dict:
    risk_map = {"FALSE_POSITIVE": 10, "NEEDS_REVIEW": 50, "TRUE_POSITIVE": 85}
    verdict = ml_result.get("verdict", "NEEDS_REVIEW")
    return {
        "verdict": verdict,
        "confidence": ml_result.get("confidence", 0.5),
        "risk_score": risk_map.get(verdict, 50),
        "reasoning": reasoning or f"ML classifier verdict used (LLM unavailable). XGBoost classified as {verdict} with {ml_result.get('confidence', 0.5):.1%} confidence.",
        "root_cause": "Not determined — LLM unavailable, root cause analysis requires LLM reasoning.",
        "contributing_factors": [],
    }
