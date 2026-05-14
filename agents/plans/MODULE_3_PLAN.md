# Module 3 Plan — Technical Architecture & Implementation

## Goal
Wire all components into a running local system: FastAPI backend exposing SSE + REST endpoints, PostgreSQL database with full schema, ReportLab PDF generator, Docker Compose for one-command startup, and a validated `.env` configuration.

---

## Deliverables

| # | Deliverable | Path |
|---|---|---|
| 1 | FastAPI main app | `backend/app/main.py` |
| 2 | App config (Pydantic Settings) | `backend/app/config.py` |
| 3 | PostgreSQL schema | `data/plant_history/schema.sql` |
| 4 | Database service | `backend/app/services/database_service.py` |
| 5 | Pinecone service | `backend/app/services/pinecone_service.py` |
| 6 | PDF service | `backend/app/services/pdf_service.py` |
| 7 | Pydantic schemas | `backend/app/schemas/` (4 files) |
| 8 | Docker Compose | `docker-compose.yml` |
| 9 | Environment template | `.env.example` |
| 10 | Backend requirements | `backend/requirements.txt` |

---

## Step-by-Step Plan

### Step 1 — FastAPI Application
File: `backend/app/main.py`

Endpoints to implement:

| Method | Path | Purpose |
|---|---|---|
| GET | `/stream/sensor` | SSE: streams sensor batches (supports `?scenario=` param) |
| POST | `/api/issues/analyze` | Triggers the 3-agent pipeline as a background task |
| GET | `/api/issues/{issue_id}` | Polls pipeline run status and result |
| POST | `/api/issues/{issue_id}/approve` | Human-in-the-loop approval gate |
| GET | `/api/reports/{issue_id}/pdf` | Downloads generated PDF |
| POST | `/api/simulation/start` | Returns SSE URL (informational) |

**CORS config:** allow `http://localhost:5173` (Vite dev server), all methods and headers.

**SSE event generator logic:**
- `scenario=pressure_drop` → call `demo_scenario_line_b_pressure_drop()`, yield once, return
- All other scenarios → call `generate_stream()`, yield batches indefinitely via `run_in_executor`

**Pipeline trigger:**
- Generate `issue_id` as `ISSUE-{date}-{6-char-uuid}`
- Add `_run_pipeline_task` to `BackgroundTasks`
- Return `{"issue_id": ..., "status": "RUNNING"}` immediately

### Step 2 — Config
File: `backend/app/config.py`

Use `pydantic_settings.BaseSettings` to load:
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`, `PINECONE_INDEX`
- `DATABASE_URL`
- `REPORT_DIR` (default: `/tmp/reports`)
- `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` (optional)

### Step 3 — PostgreSQL Schema
File: `data/plant_history/schema.sql`

Tables (in creation order to satisfy FK constraints):

1. `plants` — `id TEXT PK`, `name`, `location`, `timezone`
2. `production_lines` — `id TEXT PK`, `plant_id FK`, `name`, `product_type`
3. `quality_thresholds` — UUID PK, `line_id FK`, `metric`, `warning_low/high`, `critical_low/high`, `unit`
4. `maintenance_history` — UUID PK, `line_id FK`, `machine_id`, `event_date DATE`, `event_type`, `description`, `resolved_by`, `resolution_note`
5. `production_issues` — `issue_id TEXT PK`, `plant_id`, `line_id`, `problem_statement`, `timeframe_start/end TIMESTAMP`, `severity`, `status TEXT DEFAULT 'RUNNING'`, `approval_status DEFAULT 'pending'`, `approver`, `approval_notes`, `created_at`
6. `anomaly_events` — UUID PK, `issue_id FK`, `machine_id`, `anomaly_type`, `metric_name`, `metric_value`, `threshold_value`, `timestamp`, `severity`
7. `pipeline_runs` — UUID PK, `issue_id FK`, `scanner_output JSONB`, `investigator_output JSONB`, `technician_output JSONB`, `retrieved_context TEXT`, `pdf_path`, `created_at`
8. `maintenance_requests` — `request_id TEXT PK`, `issue_id FK`, `asset_id`, `priority`, `request_text`, `status DEFAULT 'PENDING'`, `created_at`
9. `audit_log` — UUID PK, `issue_id`, `event_type`, `actor`, `payload JSONB`, `created_at` (immutable — no UPDATE/DELETE)

### Step 4 — Database Service
File: `backend/app/services/database_service.py`

Functions:
- `save_run(issue_id, result)` — upsert to `production_issues` and `pipeline_runs`
- `get_run(issue_id)` — fetch issue + pipeline run joined
- `update_approval(issue_id, decision, approver, notes)` — update `production_issues.approval_status`, write to `audit_log`

Use `asyncpg` with a connection pool initialized at app startup (`@app.on_event("startup")`).

### Step 5 — Pinecone Service
File: `backend/app/services/pinecone_service.py`

Function:
```python
def retrieve_similar(
    query: str,
    top_k: int = 4,
    filter_meta: dict = None,
) -> list[dict]:
```
- Embed query with `OpenAIEmbeddings(model="text-embedding-3-small")`
- Query Pinecone index with `filter=filter_meta`
- Return list of `{"text": ..., "score": ..., "source": ...}` dicts

### Step 6 — PDF Service
File: `backend/app/services/pdf_service.py`

Sections in the generated PDF (A4, branded with navy header):
1. Header — issue ID, timestamp
2. Verdict banner (colour-coded: red=Stabilize, amber=Investigate, teal=Prevent Recurrence)
3. Detected Anomalies (from scanner)
4. Root Cause Hypotheses with confidence % (from investigator)
5. Recommendations — 3-tier (stabilize / investigate / prevent_recurrence)
6. Shift Handoff Note (from technician)
7. Maintenance Request (CMMS-ready)
8. Corrective Action Plan (8D/CAPA structure)
9. Compliance References
10. Footer — "Generated by Manufacturing Issue Resolution System · Confidential"

Use `reportlab.platypus.SimpleDocTemplate` with `Paragraph`, `Table`, `HRFlowable`, `Spacer`.

Write PDF to `{REPORT_DIR}/action_plan_{run_id[:12]}.pdf`.

### Step 7 — Pydantic Schemas
Directory: `backend/app/schemas/`

| File | Model | Purpose |
|---|---|---|
| `issue_schema.py` | `AnalyzeRequest`, `ApprovalRequest` | FastAPI request bodies |
| `scanner_schema.py` | `ScannerOutput` | Validates scanner JSON |
| `investigator_schema.py` | `InvestigatorOutput`, `RootCauseHypothesis`, `ConfidenceBreakdown` | Validates investigator JSON |
| `technician_schema.py` | `TechnicianOutput`, `ShiftHandoffNote`, `MaintenanceRequest`, `CorrectiveActionPlan` | Validates technician JSON |

### Step 8 — Docker Compose
File: `docker-compose.yml`

Services:
- `postgres:16` — expose 5432, named volume `pgdata`
- `backend` — build `./backend`, env_file `.env`, depends on postgres, mount `./reports:/tmp/reports`, run `uvicorn app.main:app --reload`
- `frontend` — build `./frontend`, depends on backend, run `npm run dev -- --host`

**Startup order:** postgres → backend → frontend

### Step 9 — Environment Template
File: `.env.example`

```dotenv
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=
DATABASE_URL=
REPORT_DIR=/tmp/reports

# Optional: LangSmith observability
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=mfg-issue-resolution
```

### Step 10 — Backend Requirements
File: `backend/requirements.txt`

```
fastapi
uvicorn[standard]
pydantic-settings
asyncpg
langchain
langchain-openai
langgraph
langgraph[postgres]
openai
pinecone
tiktoken
tenacity
structlog
reportlab
python-dotenv
```

---

## Full Repository Structure

```
manufacturing-issue-resolution-assistant/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/api.ts
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── simulation.py
│   │   │   ├── issues.py
│   │   │   └── reports.py
│   │   ├── agents/
│   │   │   ├── scanner_agent.py
│   │   │   ├── investigator_agent.py
│   │   │   └── technician_agent.py
│   │   ├── workflows/
│   │   │   └── manufacturing_graph.py
│   │   ├── services/
│   │   │   ├── simulation_service.py
│   │   │   ├── pinecone_service.py
│   │   │   ├── pdf_service.py
│   │   │   └── database_service.py
│   │   └── schemas/
│   │       ├── issue_schema.py
│   │       ├── scanner_schema.py
│   │       ├── investigator_schema.py
│   │       └── technician_schema.py
│   └── requirements.txt
├── data/
│   ├── plant_history/seed.sql
│   ├── pinecone_seed/seed_pinecone.py
│   ├── maintenance_records/
│   ├── prior_incidents/
│   └── sop_documents/
├── reports/generated_pdfs/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Acceptance Criteria

- [ ] `docker-compose up` starts all 3 services without errors
- [ ] `GET /stream/sensor` returns SSE events at ~1.5s intervals
- [ ] `POST /api/issues/analyze` returns `issue_id` immediately (non-blocking)
- [ ] `GET /api/issues/{issue_id}` reflects pipeline status changes (RUNNING → DONE)
- [ ] `POST /api/issues/{issue_id}/approve` writes to `audit_log` and updates `approval_status`
- [ ] `GET /api/reports/{issue_id}/pdf` streams a valid PDF file
- [ ] PDF contains all 9 content sections and opens without error
- [ ] PostgreSQL schema creates all 9 tables without constraint violations
- [ ] Pinecone service returns results filtered by `line_id`
- [ ] All Pydantic schemas validate correctly against agent JSON output

---

## API Quick Reference

```
GET  /stream/sensor?scenario=live
GET  /stream/sensor?scenario=pressure_drop
POST /api/issues/analyze              body: AnalyzeRequest
GET  /api/issues/{issue_id}
POST /api/issues/{issue_id}/approve   body: ApprovalRequest
GET  /api/reports/{issue_id}/pdf
POST /api/simulation/start
```
