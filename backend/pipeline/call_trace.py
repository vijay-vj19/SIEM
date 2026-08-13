"""
Lightweight call-tracing decorator: logs CALL / RETURN / RAISE for a
function at DEBUG level, regardless of whether it succeeds or fails.

Deliberately does NOT log argument or return values. Several pipeline
functions receive the raw ticket (real IPs, usernames, command lines)
before the guardrail redacts it — a blanket arg/return dump would risk
leaking PII into the log file, defeating the point of the Presidio step.
For "what happened", pair this with the existing per-stage narration in
main.py::_run_pipeline and the curated DEBUG detail already logged inside
each stage (features, candidates, token usage, redacted fields).

Works on both sync and async functions (two FastAPI route handlers are
async def).
"""

import functools
import inspect
import logging
import time


def trace_calls(func):
    logger = logging.getLogger(func.__module__)

    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.debug(f"CALL {func.__qualname__}")
            t0 = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"RETURN {func.__qualname__} ({int((time.perf_counter() - t0) * 1000)}ms)")
                return result
            except Exception:
                logger.debug(f"RAISE {func.__qualname__} ({int((time.perf_counter() - t0) * 1000)}ms)")
                raise
        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"CALL {func.__qualname__}")
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            logger.debug(f"RETURN {func.__qualname__} ({int((time.perf_counter() - t0) * 1000)}ms)")
            return result
        except Exception:
            logger.debug(f"RAISE {func.__qualname__} ({int((time.perf_counter() - t0) * 1000)}ms)")
            raise
    return wrapper
