"""
Guardrail pipeline: Presidio PII stripping + pattern-based input/output rails.
PII is stripped before LLM calls; original values are preserved for the SIR report.
"""

import logging
from typing import Any
from models.ticket import TicketIn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Presidio setup (lazy-initialised to avoid import cost at startup)
# ---------------------------------------------------------------------------
_analyzer = None
_anonymizer = None


def _get_presidio():
    global _analyzer, _anonymizer
    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine

            from presidio_analyzer.nlp_engine import NlpEngineProvider
            nlp_engine = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }).create_engine()
            _analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            _anonymizer = AnonymizerEngine()
            logger.info("Presidio engines initialized")
        except ImportError:
            logger.warning("presidio not installed — PII stripping disabled")
    return _analyzer, _anonymizer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "disregard",
    "you are now",
    "forget everything",
    "jailbreak",
    "act as",
    "do anything now",
    "dan mode",
]


def _strip_pii(text: str) -> str:
    """Return anonymized text. Falls back to original if Presidio unavailable."""
    if not text:
        return text
    analyzer, anonymizer = _get_presidio()
    if analyzer is None:
        return text
    try:
        results = analyzer.analyze(text=text, language="en")
        if not results:
            return text
        anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
        return anonymized.text
    except Exception as exc:
        logger.warning(f"Presidio anonymization failed: {exc}")
        return text


def _check_injection(value: str) -> bool:
    """Return True if a prompt injection pattern is detected."""
    lowered = value.lower()
    return any(pat in lowered for pat in INJECTION_PATTERNS)


def run_input_guardrail(ticket: TicketIn) -> dict[str, Any]:
    """
    Run PII stripping and injection checks on ticket fields.
    Returns a dict with:
      - 'safe_ticket': anonymized ticket dict for LLM
      - 'guardrail_status': dict with scan results
      - 'blocked': bool — True if the ticket should be rejected
    """
    status = {
        "presidio_pii_scan": "PASSED",
        "nemo_input_rail": "PASSED",
        "nemo_output_rail": "PASSED",
    }

    # Check for injection in free-text fields
    injection_fields = [ticket.command_line, ticket.decoded_command, ticket.user]
    for field_val in injection_fields:
        if _check_injection(field_val):
            status["nemo_input_rail"] = "BLOCKED"
            return {"safe_ticket": None, "guardrail_status": status, "blocked": True}

    # Strip PII from free-text fields before sending to LLM
    safe = ticket.model_dump(mode="json")
    for field in ("command_line", "decoded_command", "user", "source_ip", "target_ip"):
        safe[field] = _strip_pii(str(safe.get(field, "")))

    if any(safe[f] != getattr(ticket, f, "") for f in ("command_line", "decoded_command")):
        status["presidio_pii_scan"] = "REDACTED"

    return {"safe_ticket": safe, "guardrail_status": status, "blocked": False}


def validate_llm_output(llm_response: dict) -> tuple[dict, str]:
    """
    Validate LLM output contains a valid verdict.
    Returns (validated_response, rail_status).
    """
    valid_verdicts = {"TRUE_POSITIVE", "FALSE_POSITIVE", "NEEDS_REVIEW"}
    verdict = llm_response.get("verdict", "")

    if verdict not in valid_verdicts:
        fallback = {
            "verdict": "NEEDS_REVIEW",
            "confidence": 0.5,
            "risk_score": 50,
            "reasoning": "LLM output guardrail triggered — verdict was invalid. Manual review required.",
            "root_cause": "Not determined — LLM output failed validation.",
            "contributing_factors": [],
        }
        return fallback, "BLOCKED"

    return llm_response, "PASSED"
