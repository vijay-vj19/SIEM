# SOC Triage AI — POC

A full-stack SOC Level-1 triage automation system: upload SIEM tickets via Excel
or a manual form, and the ML + RAG + LLM pipeline returns a verdict
(True Positive / False Positive / Needs Review) plus a full Security Incident Report.

## Architecture

```
Excel / Form → FastAPI backend
                 ├── Presidio (PII strip) + pattern-based injection check
                 ├── XGBoost classifier
                 ├── LlamaIndex + Supabase RAG (similar incidents)
                 ├── GPT-4o-mini (verdict + reasoning)
                 └── SIR report generator
                          ↓
              React frontend (dark SOC dashboard)
```

## Quick Start

### 1. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (required by Presidio)
python -m spacy download en_core_web_lg

# Copy and fill in env vars
# Edit backend/.env with your actual keys

# Train the XGBoost classifier (one time)
python scripts/train_model.py

# (Optional) Seed Supabase RAG with mock tickets (requires Supabase config)
python scripts/seed_rag.py

# Start backend
uvicorn main:app --reload --port 8000
```

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

## Supabase Setup (for RAG)

Run this SQL once in the Supabase SQL editor:

```sql
create extension if not exists vector;

create table soc_incidents (
  id bigserial primary key,
  ticket_id text,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

create index on soc_incidents
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

Then run `python scripts/seed_rag.py`.

> The app works without Supabase — RAG falls back to keyword-based
> similarity matching against the mock tickets.

## Audit Log Setup (Supabase)

Every completed triage run writes one durable row to an `audit_log` table —
this is the system of record (see [Logging](#logging) below for why it takes
priority over the log file). Run this SQL once in the Supabase SQL editor:

```sql
create table audit_log (
  id bigserial primary key,
  ticket_id text,
  verdict text,
  confidence float,
  risk_score int,
  xgboost_verdict text,
  guardrail_blocked bool,
  processing_time_ms int,
  raw jsonb,
  created_at timestamptz default now()
);
```

Uses the same `SUPABASE_DB_CONNECTION` as RAG — no extra env vars needed. If
that variable is unset or Supabase is unreachable, `pipeline/audit.py` logs a
warning and triage continues normally; auditing never blocks a triage run.

## Environment Variables (`backend/.env`)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (required for LLM triage) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_DB_CONNECTION` | PostgreSQL connection string for pgvector |
| `MODEL_PATH` | Path to trained XGBoost model (default `./models/xgboost_classifier.pkl`) |
| `CORS_ORIGINS` | Allowed origins (default `http://localhost:5173`) |
| `LANGSMITH_API_KEY` | LangSmith API key (enables LLM tracing + the LLM Performance dashboard) |
| `LANGSMITH_TRACING` | Set to `true` to enable tracing (SDK no-ops otherwise, even with a key set) |
| `LANGSMITH_PROJECT` | LangSmith project name runs are grouped under (default `soc-triage-ai`) |

> LangSmith is optional — without `LANGSMITH_API_KEY`, triage works exactly as
> before and `/api/langsmith/*` endpoints return `configured: false`.

| `LOG_DIR` | Directory for the rotating log file (default `./logs`). See [Logging](#logging). |

## Excel Upload Format

The uploaded Excel file must have exactly these column headers:

```
ticket_id, severity, status, created_time, rule_triggered, mitre_attack,
user, user_type, source_asset, source_ip, target_asset, target_ip,
process, command_line, decoded_command, hour_of_day, day_of_week,
historical_tp_count, historical_fp_count
```

## Pipeline

Each ticket flows through 6 sequential stages:

1. **Guardrail (input)** — Presidio strips PII; pattern matching blocks prompt injection
2. **XGBoost** — 10-feature ML classifier predicts FP / NR / TP
3. **RAG** — LlamaIndex retrieves top-3 similar past incidents from Supabase
4. **LLM** — GPT-4o-mini confirms/overrides verdict with reasoning
5. **Guardrail (output)** — validates LLM response format
6. **SIR Generator** — builds markdown Security Incident Report

## Logging

Every triage run is logged twice, for two different purposes:

1. **Rotating log file** (`{LOG_DIR}/soc_triage.log`, ~5MB × 3 backups, console
   output too) — narrates each of the 6 pipeline stages per ticket
   (`[ticket_id] guardrail: ...`, `xgboost: ...`, `rag: ...`, `llm: ...`,
   `output_rail: ...`, `sir: ...`, ending in `DONE verdict=... time=...ms`).
   Good for tailing recent activity and debugging a specific run.
2. **`audit_log` table in Supabase** (see [Audit Log Setup](#audit-log-setup-supabase))
   — one durable row per completed run. This is the actual system of record.

**On Render, `LOG_DIR` defaults to `./logs`, which is ephemeral** — wiped on
every restart/redeploy, since this project doesn't provision a paid Render
persistent disk. The `audit_log` table is what survives. If you do want the
log file itself to persist, add a Render persistent disk (Dashboard → your
service → Disks — starts around $0.25/GB/month, 1GB minimum), mount it (e.g.
at `/var/data`), and set `LOG_DIR=/var/data/logs` in the service's
environment variables.

Third-party loggers (`presidio-analyzer`, `httpx`) are set to `WARNING` to
keep the file readable — they're chatty at `INFO`.

## Graceful Degradation

- **No OpenAI key** → XGBoost verdict used directly, no LLM reasoning
- **No Supabase** → keyword-based fallback for similar incident retrieval
- **Model not trained** → NEEDS_REVIEW returned for all tickets (run `train_model.py`)
- **Supabase unavailable for auditing** → `pipeline/audit.py` logs a warning and triage continues; no audit row is written for that run
