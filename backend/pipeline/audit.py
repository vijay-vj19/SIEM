"""
Durable audit trail: inserts one row per completed triage run into the
Supabase `audit_log` table (see README for the CREATE TABLE SQL).

Fail-safe by design — if Supabase is unreachable or unconfigured, this logs
a warning and returns. Auditing must never break triage.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    return bool(os.getenv("SUPABASE_DB_CONNECTION"))


def log_audit_entry(
    ticket_id: str,
    verdict: str,
    confidence: float,
    risk_score: int,
    xgboost_verdict: str,
    guardrail_blocked: bool,
    processing_time_ms: int,
    raw: dict[str, Any],
) -> None:
    """Insert one audit_log row for a completed triage run. Never raises."""
    if not _is_configured():
        logger.warning(f"[{ticket_id}] audit: SUPABASE_DB_CONNECTION not set — skipping audit log")
        return

    try:
        import psycopg2

        conn = psycopg2.connect(os.getenv("SUPABASE_DB_CONNECTION"))
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (ticket_id, verdict, confidence, risk_score, xgboost_verdict,
                         guardrail_blocked, processing_time_ms, raw)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        ticket_id,
                        verdict,
                        confidence,
                        risk_score,
                        xgboost_verdict,
                        guardrail_blocked,
                        processing_time_ms,
                        json.dumps(raw, default=str),
                    ),
                )
            conn.commit()
            logger.info(f"[{ticket_id}] audit: row written")
        finally:
            conn.close()
    except Exception:
        logger.exception(f"[{ticket_id}] audit: failed to write audit_log row — continuing")
