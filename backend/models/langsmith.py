from pydantic import BaseModel


class RunsOverTimeBucket(BaseModel):
    bucket: str  # ISO timestamp for the start of the bucket
    count: int


class LangSmithSummary(BaseModel):
    configured: bool
    error: str | None = None
    total_runs: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    avg_latency_ms: int = 0
    p50_latency_ms: int = 0
    p95_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    runs_over_time: list[RunsOverTimeBucket] = []


class LangSmithRun(BaseModel):
    run_id: str
    ticket_id: str | None = None
    status: str
    latency_ms: int
    total_tokens: int
    cost_usd: float
    started_at: str
    langsmith_url: str | None = None


class LangSmithRunsResponse(BaseModel):
    configured: bool
    error: str | None = None
    runs: list[LangSmithRun] = []
