"""
SOC Triage AI — FastAPI backend.
Endpoints:
  POST /api/triage/excel       — process uploaded Excel file
  POST /api/triage/single      — process single ticket JSON
  GET  /api/triage/{id}        — retrieve cached result
  GET  /api/triage/{id}/pdf    — download cached result as a PDF report
  GET  /api/health             — health check
"""

import logging
import os
import time
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

try:
    from dotenv import load_dotenv
    load_dotenv(".env", override=True)
except ImportError:
    pass
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory result cache keyed by ticket_id
_result_cache: dict[str, dict] = {}

# Raw pipeline materials kept separately (not part of the API response schema),
# used only to regenerate the PDF report on demand.
_pdf_context_cache: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SOC Triage AI backend…")
    from pipeline.classifier import load_model
    from pipeline.rag import init_rag

    load_model()
    init_rag()
    logger.info("Backend ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="SOC Triage AI",
    version="0.1.0",
    description="Level-1 SOC triage automation: ML + RAG + LLM pipeline",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

from models.ticket import REQUIRED_EXCEL_COLUMNS, TicketIn
from models.response import GuardrailStatus, SimilarIncident, TriageResult, TriageResponse, TriageSummary


def _run_pipeline(ticket: TicketIn) -> dict[str, Any]:
    """Run the full triage pipeline for a single ticket. Returns a result dict."""
    t0 = time.perf_counter()

    from pipeline.guardrail import run_input_guardrail, validate_llm_output
    from pipeline.classifier import predict
    from pipeline.rag import retrieve_similar, ticket_to_text
    from pipeline.llm import run_llm_triage
    from pipeline.sir_generator import generate_sir

    # Step 1: Guardrail — PII strip + injection check
    guard = run_input_guardrail(ticket)
    if guard["blocked"]:
        raise HTTPException(
            status_code=400,
            detail=f"Ticket {ticket.ticket_id} blocked by input guardrail (prompt injection detected).",
        )

    safe_ticket: dict = guard["safe_ticket"]
    guardrail_status: dict = guard["guardrail_status"]

    # Step 2: XGBoost classifier
    ml_result = predict(ticket)

    # Step 3: RAG — similar incidents
    ticket_text = ticket_to_text(ticket.model_dump(mode="json"))
    similar = retrieve_similar(ticket_text)

    # Step 4: LLM triage
    llm_result = run_llm_triage(safe_ticket, ml_result, similar)

    # Step 5: Output guardrail
    llm_result, output_rail_status = validate_llm_output(llm_result)
    guardrail_status["nemo_output_rail"] = output_rail_status

    # Step 6: SIR report
    sir = generate_sir(
        ticket=ticket.model_dump(mode="json"),
        llm_result=llm_result,
        ml_result=ml_result,
        similar_incidents=similar,
        guardrail_status=guardrail_status,
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    result = {
        "ticket_id": ticket.ticket_id,
        "verdict": llm_result["verdict"],
        "confidence": llm_result["confidence"],
        "xgboost_score": ml_result.get("xgboost_score", ml_result["confidence"]),
        "llm_reasoning": llm_result["reasoning"],
        "root_cause": llm_result.get("root_cause", ""),
        "contributing_factors": llm_result.get("contributing_factors", []),
        "mitre_attack": ticket.mitre_attack,
        "risk_score": llm_result["risk_score"],
        "sir_report": sir,
        "processing_time_ms": elapsed_ms,
        "similar_past_incidents": similar,
        "guardrail_status": guardrail_status,
    }

    _result_cache[ticket.ticket_id] = result
    _pdf_context_cache[ticket.ticket_id] = {
        "ticket": ticket.model_dump(mode="json"),
        "llm_result": llm_result,
        "ml_result": ml_result,
        "similar": similar,
        "guardrail_status": guardrail_status,
    }
    return result


def _build_summary(results: list[dict]) -> dict:
    tp = sum(1 for r in results if r["verdict"] == "TRUE_POSITIVE")
    fp = sum(1 for r in results if r["verdict"] == "FALSE_POSITIVE")
    nr = sum(1 for r in results if r["verdict"] == "NEEDS_REVIEW")
    return {"total": len(results), "true_positive": tp, "false_positive": fp, "needs_review": nr}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "SOC Triage AI"}


@app.post("/api/triage/single")
async def triage_single(ticket: TicketIn):
    """Process a single ticket submitted as JSON."""
    result = _run_pipeline(ticket)
    summary = _build_summary([result])
    return {"results": [result], "summary": summary}


@app.post("/api/triage/excel")
async def triage_excel(file: UploadFile = File(...)):
    """
    Upload an Excel file (.xlsx / .xls) containing multiple tickets.
    Returns triage results for every row.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are accepted.")

    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse Excel file: {exc}")

    # Column validation
    received = list(df.columns)
    missing = [col for col in REQUIRED_EXCEL_COLUMNS if col not in received]
    if missing:
        return JSONResponse(
            status_code=422,
            content={
                "error": f"Missing required columns: {missing}",
                "expected_columns": REQUIRED_EXCEL_COLUMNS,
                "received_columns": received,
            },
        )

    results = []
    errors = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        # Coerce numeric fields
        for field in ("hour_of_day", "historical_tp_count", "historical_fp_count"):
            row_dict[field] = int(row_dict.get(field, 0))

        try:
            ticket = TicketIn(**row_dict)
            result = _run_pipeline(ticket)
            results.append(result)
        except HTTPException as exc:
            errors.append({"row": idx + 2, "ticket_id": row_dict.get("ticket_id"), "error": exc.detail})
        except Exception as exc:
            errors.append({"row": idx + 2, "ticket_id": row_dict.get("ticket_id"), "error": str(exc)})

    summary = _build_summary(results)
    response: dict[str, Any] = {"results": results, "summary": summary}
    if errors:
        response["errors"] = errors

    return response


@app.get("/api/triage/{ticket_id}")
async def get_result(ticket_id: str):
    """Retrieve a cached triage result by ticket ID."""
    result = _result_cache.get(ticket_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No result found for ticket {ticket_id}.")
    return result


@app.get("/api/triage/{ticket_id}/pdf")
async def get_result_pdf(ticket_id: str):
    """Download the Security Incident Report for a ticket as a PDF."""
    context = _pdf_context_cache.get(ticket_id)
    if context is None:
        raise HTTPException(status_code=404, detail=f"No result found for ticket {ticket_id}.")

    from pipeline.pdf_generator import generate_pdf

    pdf_bytes = generate_pdf(
        ticket=context["ticket"],
        llm_result=context["llm_result"],
        ml_result=context["ml_result"],
        similar_incidents=context["similar"],
        guardrail_status=context["guardrail_status"],
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="SIR-{ticket_id}.pdf"'},
    )
