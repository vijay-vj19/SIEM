# SOC Triage AI — POC

A full-stack SOC Level-1 triage automation system: upload SIEM tickets via Excel
or a manual form, and the ML + RAG + LLM pipeline returns a verdict
(True Positive / False Positive / Needs Review) plus a full Security Incident Report.

## Architecture

```
Excel / Form → FastAPI backend
                 ├── Presidio (PII strip)
                 ├── NeMo Guardrails (injection check)
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

### 3. Docker (optional)

```bash
docker-compose up --build
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

## Environment Variables (`backend/.env`)

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (required for LLM triage) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `SUPABASE_DB_CONNECTION` | PostgreSQL connection string for pgvector |
| `MODEL_PATH` | Path to trained XGBoost model (default `./models/xgboost_classifier.pkl`) |
| `CORS_ORIGINS` | Allowed origins (default `http://localhost:5173`) |

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

1. **Guardrail (input)** — Presidio strips PII; NeMo blocks prompt injection
2. **XGBoost** — 10-feature ML classifier predicts FP / NR / TP
3. **RAG** — LlamaIndex retrieves top-3 similar past incidents from Supabase
4. **LLM** — GPT-4o-mini confirms/overrides verdict with reasoning
5. **Guardrail (output)** — validates LLM response format
6. **SIR Generator** — builds markdown Security Incident Report

## Graceful Degradation

- **No OpenAI key** → XGBoost verdict used directly, no LLM reasoning
- **No Supabase** → keyword-based fallback for similar incident retrieval
- **Model not trained** → NEEDS_REVIEW returned for all tickets (run `train_model.py`)
