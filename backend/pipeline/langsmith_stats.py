"""
LangSmith run stats: pulls real GPT-4o-mini call data (latency, tokens, cost,
errors) from the LangSmith API for the LLM Performance dashboard.

Degrades gracefully — every function returns configured=False instead of
raising when LANGSMITH_API_KEY isn't set, matching the rest of the pipeline
(see rag.py::init_rag, llm.py::run_llm_triage).
"""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

logger = logging.getLogger(__name__)

# GPT-4o-mini published pricing, used only when LangSmith doesn't report its
# own cost for a run (e.g. no pricing configured on the workspace).
PRICE_PER_1M_PROMPT_TOKENS = 0.15
PRICE_PER_1M_COMPLETION_TOKENS = 0.60

RANGE_TO_TIMEDELTA = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

TICKET_ID_RE = re.compile(r'"ticket_id":\s*"([^"]+)"')


def _is_configured() -> bool:
    return bool(os.getenv("LANGSMITH_API_KEY"))


def _get_client():
    from langsmith import Client

    return Client()


def _project_name() -> str:
    return os.getenv("LANGSMITH_PROJECT", "soc-triage-ai")


def _start_time(range_key: str) -> datetime:
    delta = RANGE_TO_TIMEDELTA.get(range_key, RANGE_TO_TIMEDELTA["24h"])
    return datetime.now(timezone.utc) - delta


def _latency_ms(run: Any) -> int:
    if not run.start_time or not run.end_time:
        return 0
    return int((run.end_time - run.start_time).total_seconds() * 1000)


def _cost_usd(run: Any) -> float:
    if getattr(run, "total_cost", None) is not None:
        return float(run.total_cost)
    prompt = run.prompt_tokens or 0
    completion = run.completion_tokens or 0
    return round(
        (prompt / 1_000_000) * PRICE_PER_1M_PROMPT_TOKENS
        + (completion / 1_000_000) * PRICE_PER_1M_COMPLETION_TOKENS,
        6,
    )


def _extract_ticket_id(run: Any) -> str | None:
    try:
        messages = run.inputs.get("messages", [])
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else ""
            match = TICKET_ID_RE.search(content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    idx = min(int(len(sorted_values) * pct), len(sorted_values) - 1)
    return sorted_values[idx]


def _as_utc(dt: datetime) -> datetime:
    """LangSmith returns naive datetimes that represent UTC wall-clock time —
    tag them explicitly so downstream isoformat()/timezone conversions (both
    here and in the browser) are correct instead of being silently
    misinterpreted as local time."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _resolve_tz(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(f"Unknown timezone '{tz_name}' — falling back to UTC")
        return ZoneInfo("UTC")


def _bucket_key(dt_utc: datetime, range_key: str, tz: ZoneInfo) -> str:
    """Bucket boundary in the caller's local timezone, so 'today' in the
    runs-over-time chart matches the viewer's own calendar day/hour rather
    than the server's UTC day."""
    local_dt = _as_utc(dt_utc).astimezone(tz)
    if range_key == "24h":
        bucket_start = local_dt.replace(minute=0, second=0, microsecond=0)
    else:
        bucket_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return bucket_start.isoformat()


def get_summary(range_key: str, tz_name: str = "UTC") -> dict:
    if not _is_configured():
        return {"configured": False}

    try:
        client = _get_client()
        runs = list(
            client.list_runs(
                project_name=_project_name(),
                run_type="llm",
                start_time=_start_time(range_key),
                limit=2000,  # safety cap — summary stats, not a full export
            )
        )
    except Exception as exc:
        logger.error(f"LangSmith list_runs failed: {exc}")
        return {"configured": True, "error": str(exc)}

    total_runs = len(runs)
    error_count = sum(1 for r in runs if r.error)
    latencies = sorted(_latency_ms(r) for r in runs)
    prompt_tokens = sum(r.prompt_tokens or 0 for r in runs)
    completion_tokens = sum(r.completion_tokens or 0 for r in runs)
    total_cost = round(sum(_cost_usd(r) for r in runs), 4)

    tz = _resolve_tz(tz_name)
    buckets: dict[str, int] = {}
    for r in runs:
        if r.start_time:
            key = _bucket_key(r.start_time, range_key, tz)
            buckets[key] = buckets.get(key, 0) + 1
    runs_over_time = [{"bucket": k, "count": v} for k, v in sorted(buckets.items())]

    return {
        "configured": True,
        "total_runs": total_runs,
        "error_count": error_count,
        "error_rate": round(error_count / total_runs, 4) if total_runs else 0.0,
        "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
        "p50_latency_ms": _percentile(latencies, 0.5),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_cost_usd": total_cost,
        "runs_over_time": runs_over_time,
    }


def get_recent_runs(range_key: str, limit: int) -> dict:
    if not _is_configured():
        return {"configured": False, "runs": []}

    try:
        client = _get_client()
        project = _project_name()
        runs = list(
            client.list_runs(
                project_name=project,
                run_type="llm",
                start_time=_start_time(range_key),
                limit=limit,
            )
        )
    except Exception as exc:
        logger.error(f"LangSmith list_runs failed: {exc}")
        return {"configured": True, "error": str(exc), "runs": []}

    out = []
    for r in runs:
        try:
            url = client.get_run_url(run=r, project_name=project)
        except Exception:
            url = None
        out.append(
            {
                "run_id": str(r.id),
                "ticket_id": _extract_ticket_id(r),
                "status": "error" if r.error else "success",
                "latency_ms": _latency_ms(r),
                "total_tokens": (r.prompt_tokens or 0) + (r.completion_tokens or 0),
                "cost_usd": _cost_usd(r),
                "started_at": _as_utc(r.start_time).isoformat() if r.start_time else "",
                "langsmith_url": url,
            }
        )

    return {"configured": True, "runs": out}
