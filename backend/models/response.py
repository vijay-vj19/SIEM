from pydantic import BaseModel
from typing import Literal, Optional
from enum import Enum


class VerdictEnum(str, Enum):
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SimilarIncident(BaseModel):
    ticket_id: str
    similarity: float
    verdict: str


class GuardrailStatus(BaseModel):
    presidio_pii_scan: str = "PASSED"
    nemo_input_rail: str = "PASSED"
    nemo_output_rail: str = "PASSED"


class TriageResult(BaseModel):
    ticket_id: str
    verdict: VerdictEnum
    confidence: float
    xgboost_score: float
    llm_reasoning: str
    mitre_attack: str
    risk_score: int
    sir_report: str
    processing_time_ms: int
    similar_past_incidents: list[SimilarIncident]
    guardrail_status: GuardrailStatus = GuardrailStatus()


class TriageSummary(BaseModel):
    total: int
    true_positive: int
    false_positive: int
    needs_review: int


class TriageResponse(BaseModel):
    results: list[TriageResult]
    summary: TriageSummary


class ErrorResponse(BaseModel):
    error: str
    expected_columns: Optional[list[str]] = None
    received_columns: Optional[list[str]] = None
