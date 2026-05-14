# Production Issue Resolution Assistant

Manufacturing-focused AI assistant for detecting simulated production issues, investigating likely root causes, generating operator-ready action plans, and enforcing a human approval gate before any external action.

The project is designed as a local demo/MVP for plant managers and manufacturing teams. It runs without a real plant connection by using simulated IoT sensor streams and seeded manufacturing history.

## What It Does

- Streams simulated sensor readings for four production lines.
- Detects anomalies such as low pressure, temperature spikes, high vibration, output drops, and data gaps.
- Runs a three-step agent workflow:
  - Scanner Agent: classifies sensor anomalies.
  - Investigator Agent: builds root-cause hypotheses and recommendations.
  - Technician Agent: creates shift handoff, maintenance request, CAPA, and PDF report.
- Shows live readings and agent status in a React dashboard.
- Requires a human approve/reject decision before downstream CMMS-style action.
- Stores relational manufacturing data with PostgreSQL schema and seed scripts.
- Provides Pinecone seed tooling for future vector KB retrieval.

## Architecture

The main system architecture is documented in [Presentation/ARCHITECTURE.md](Presentation/ARCHITECTURE.md).

High-level flow:

```text
React dashboard
  -> FastAPI SSE + REST API
    -> Scanner -> Investigator -> Technician
      -> PDF report
      -> approval gate
      -> PostgreSQL audit/state tables
```

Core services:

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Vite, React, TypeScript, Tailwind | Dashboard, live stream, approvals, PDF download |
| Backend | FastAPI | SSE stream, REST API, pipeline orchestration |
| Agents | Python workflow | Scanner, Investigator, Technician |
| Database | PostgreSQL | Plant history, pipeline runs, approvals, audit log |
| PDF | ReportLab | Corrective action/action-plan report |
| Vector KB | Pinecone seed script | Incidents, SOPs, maintenance records |

## Repository Layout

```text
backend/
  app/
    agents/                 # scanner, investigator, technician
    schemas/                # Pydantic request/output models
    services/               # simulation, database, Pinecone, PDF, LLM helpers
    workflows/              # manufacturing graph orchestration
    main.py                 # FastAPI app
  tests/

frontend/
  src/
    components/             # dashboard panels and controls
    hooks/                  # SSE and pipeline hooks
    lib/                    # API helpers

data/
  plant_history/
    schema.sql              # 9-table PostgreSQL schema
    seed.sql                # plant/line/threshold/maintenance seed data
  pinecone_seed/
    seed_pinecone.py
  scanner_rules.json
  evaluation_examples/

docs/
  APPROVAL_WORKFLOW.md
  ROADMAP.md

agents/plans/
  MODULE_1_PLAN.md
  MODULE_2_PLAN.md
  MODULE_3_PLAN.md
  MODULE_4_PLAN.md
```

## Module Status

| Module | Status | Notes |
|---|---|---|
| Module 1 - Data Simulation & Frontend | Complete | Simulator, SSE hook, dashboard components, seeds |
| Module 2 - Multi-Agent Architecture | Complete | Scanner, Investigator, Technician, workflow, tests |
| Module 3 - Technical Implementation | Complete | FastAPI endpoints, DB/Pinecone services, schemas, Docker |
| Module 4 - Roadmap & Deliverables | Complete | Approval UI, demo scenarios, docs, checklist support |

Live OpenAI/Pinecone behavior depends on valid credentials. The local implementation has deterministic fallbacks so the demo can run offline.

## Environment Variables

Create `.env` from [.env.example](.env.example):

```dotenv
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=
DATABASE_URL=
REPORT_DIR=/tmp/reports
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=mfg-issue-resolution
```

Do not commit `.env` or real API keys.

## Run With Docker Compose

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

The Compose setup starts:

- `postgres:16`
- FastAPI backend
- Vite frontend

It also loads:

- `data/plant_history/schema.sql`
- `data/plant_history/seed.sql`

## Run Locally Without Docker

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload
```

Frontend:

```bash
export PATH=/Users/saharatif/.nvm/versions/node/v20.20.2/bin:$PATH
npm --prefix frontend install
npm --prefix frontend run dev
```

The explicit Node path avoids the broken Homebrew Node install previously seen on this machine.

## API Quick Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health check |
| GET | `/stream/sensor?scenario=live` | Live SSE sensor stream |
| GET | `/stream/sensor?scenario=pressure_drop` | One-shot pressure-drop demo event |
| POST | `/api/simulation/start` | Returns SSE URL for a scenario |
| POST | `/api/issues/analyze` | Starts background agent analysis |
| GET | `/api/issues/{issue_id}` | Polls issue/pipeline status |
| POST | `/api/issues/{issue_id}/approve` | Approves or rejects the action package |
| GET | `/api/reports/{issue_id}/pdf` | Downloads generated PDF |
| POST | `/api/pipeline/run` | Synchronous pipeline run helper |

Example analyze request:

```json
{
  "problem_statement": "Pressure drop on Line B",
  "plant_id": "PLANT-01",
  "line_id": "LINE-B",
  "scenario": "pressure_drop"
}
```

Example approval request:

```json
{
  "decision": "approved",
  "approver": "Plant Manager",
  "notes": "Maintenance team cleared to inspect PRESS-VALVE-23."
}
```

## Demo Scenarios

| Scenario | Query Value | Expected Result |
|---|---|---|
| Live stream | `live` | Normal stream with occasional anomalies |
| LINE-B pressure drop | `pressure_drop` | Low pressure, Stabilize verdict |
| Temperature spike | `temp_spike` | Critical temperature anomaly |
| Missing sensor data | `data_gap` | DATA_GAP anomaly |
| High vibration | `high_vibration` | Vibration anomaly |

Recommended walkthrough:

1. Open `http://localhost:5173`.
2. Select `Demo: LINE-B Pressure Drop`.
3. Start the stream.
4. Run agent analysis.
5. Review Scanner alert, Investigator verdict, and Technician action package.
6. Approve or reject the action package.
7. Download the PDF report.

## Testing

Backend tests:

```bash
PYTHONPATH=backend python3 -m unittest discover -s backend/tests -p 'test_*.py'
```

Frontend build:

```bash
export PATH=/Users/saharatif/.nvm/versions/node/v20.20.2/bin:$PATH
npm --prefix frontend run build
```

Docker validation:

```bash
docker compose config
docker compose up --build
```

## Security Notes

- No API keys or credentials should be committed.
- `.env` is ignored.
- `.env.example` contains variable names only.
- The assistant does not control physical equipment.
- Human approval is required before CMMS-style maintenance actions.
- `audit_log` is designed as immutable in the PostgreSQL schema.

## Current Caveats

- OpenAI and Pinecone integrations require live credentials.
- The local agent behavior is deterministic and demo-friendly.
- PostgreSQL is used by Docker Compose; local non-Docker runs can fall back to in-memory run state if `DATABASE_URL` is not set.
- Pinecone seed script is available but must be run separately after credentials are configured.

## Useful Docs

- [Architecture](Presentation/ARCHITECTURE.md)
- [Approval Workflow](docs/APPROVAL_WORKFLOW.md)
- [Roadmap](docs/ROADMAP.md)
- [Module 1 Plan](agents/plans/MODULE_1_PLAN.md)
- [Module 2 Plan](agents/plans/MODULE_2_PLAN.md)
- [Module 3 Plan](agents/plans/MODULE_3_PLAN.md)
- [Module 4 Plan](agents/plans/MODULE_4_PLAN.md)
