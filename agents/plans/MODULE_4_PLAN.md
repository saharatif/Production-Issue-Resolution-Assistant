# Module 4 Plan — Roadmap, Best Practices & Deliverables

## Goal
Define the phased delivery roadmap, enforce non-negotiable best practices, document the 5 demo scenarios, and produce the final deliverables checklist so the project can be shipped, demoed, and handed off cleanly.

---

## Implementation Roadmap

### Phase 1 — MVP (Weeks 1–4)
**Scope:** Simulated data · Rule-based scanner · Three-agent pipeline · Pinecone RAG · PDF report · Frontend dashboard

| Week | Focus |
|---|---|
| 1 | Repo setup, Docker Compose, PostgreSQL schema, Pinecone seed, sensor simulator |
| 2 | Scanner Agent + Investigator Agent (LangGraph graph wired) |
| 3 | Technician Agent + PDF generation + FastAPI endpoints |
| 4 | Frontend SSE hook, TriggerButton, SensorStreamPanel, AgentPipelineStatus stepper, approval gate UI |

**MVP Feature List:**
- Start Production Stream button with 4 scenario options
- Plant and line selector
- Scanner anomaly alert card
- Agent pipeline stepper (Scanner ✅ → Investigator 🔄 → Technician ⏳)
- Investigator verdict banner with colour-coding
- Root-cause hypotheses with weighted confidence bars
- Technician action package: shift handoff, maintenance request, CAPA
- Downloadable PDF report
- Human approval gate (approve/reject before CMMS action)

---

### Phase 2 — Better Context & Retrieval (Weeks 5–8)

**Additional Knowledge Sources to Add:**
- Full SOP PDFs (chunked via `langchain.text_splitter.RecursiveCharacterTextSplitter`)
- 12-month maintenance logs
- Quality inspection reports
- Supplier delivery records
- Downtime records and shift notes
- Safety alerts and near-miss reports

**RAG Quality Improvements:**
- Metadata filtering by plant, line, machine, issue type, and date range
- Hybrid search: combine vector similarity with BM25 keyword retrieval
- Cross-encoder reranking (e.g. `sentence-transformers/ms-marco-MiniLM`) for evidence quality
- Citation tracking: return `source_document_id` and `chunk_index` with every retrieved chunk

**Pinecone Metadata Schema (extended):**
```json
{
  "plant_id": "PLANT-01",
  "line_id": "LINE-B",
  "machine_id": "PRESS-VALVE-23",
  "document_type": "maintenance_record",
  "date": "2026-04-28",
  "tags": ["pressure", "valve", "calibration"]
}
```

---

### Phase 3 — Production-Grade Integrations (Weeks 9–14)

**Real System Integrations:**
- PLC / SCADA connector (OPC-UA or MQTT bridge)
- MES integration for production order context
- CMMS integration for direct maintenance ticket creation (post human approval)
- ERP or supplier portal integration for purchase orders and delivery tracking
- Email / Microsoft Teams notification on verdict + approval
- Grafana dashboard for sensor trend visualisation

**Infrastructure Upgrades:**
- Celery + Redis for async pipeline queuing (replace FastAPI BackgroundTasks)
- Kafka or MQTT for real-time IoT data ingestion
- InfluxDB or TimescaleDB for time-series sensor storage and trend queries
- Kubernetes deployment — separate pods per agent for independent scaling

**Governance Additions:**
- Role-based access control (RBAC) — plant manager, maintenance engineer, supervisor roles
- Versioned prompt templates stored in DB with A/B testing support
- Full immutable audit trail: inputs, raw sensor snapshot, all agent outputs, approvals
- Confidence threshold gate — require confidence ≥ 0.70 before auto-escalation

---

### Phase 4 — Advanced AI & Operational Intelligence (Weeks 15+)

**Advanced Features:**
- Isolation Forest or LSTM-based time-series anomaly detector (replaces rule-based scanner)
- Predictive maintenance scoring — predict failure probability per machine per shift
- Supplier delay prediction from historical lead-time trends
- Quality defect pattern detection across shifts and lines
- Voice or mobile shift handoff assistant
- Operator feedback loop — thumbs up/down on recommendations improves future retrieval ranking

---

## Non-Negotiable Best Practices

### 1. Every Recommendation Must Cite Evidence
All agent outputs must reference:
- Specific sensor reading values and thresholds
- Prior incident IDs (e.g. `INC-2026-0312-LINE-B-004`)
- Maintenance record IDs (e.g. `MNT-2026-0428-009`)
- SOP document IDs and revision numbers
- ISO/OSHA standard clause numbers

### 2. Confidence Scores Must Be Explainable
Surface the 4-component breakdown in the UI. Plant managers must understand *why* a score is high or low, not just see a number.

```
historical_similarity:        35%
threshold_violation_strength: 25%
maintenance_history_match:    25%
data_completeness:            15%
```

### 3. Separate Time Horizons
| Tier | Owner | Timeframe |
|---|---|---|
| Stabilize | Shift operator | Act NOW |
| Investigate | Maintenance / process engineer | This shift or next |
| Prevent Recurrence | Engineering / management | Days or weeks |

### 4. LLM Must Never Control Physical Systems
The assistant recommends only. It must **never** directly:
- Write to PLC registers or SCADA setpoints
- Open/close valves, relays, or safety systems
- Send automated commands to robots or conveyors
- Override machine interlocks

All physical actions must be taken by a qualified human operator.

### 5. Human-in-the-Loop Required Before:
- Creating a CMMS maintenance ticket
- Sending supplier communication or purchase orders
- Updating SOPs or quality thresholds
- Closing corrective actions
- Escalating safety incidents to regulatory bodies

The `POST /api/issues/{issue_id}/approve` endpoint enforces this programmatically.

### 6. Log Everything — Immutably
The `audit_log` table must never be updated or deleted. It captures:
- User inputs and problem statements
- Raw sensor batch snapshot at time of trigger
- All three agent outputs (verbatim JSON)
- Retrieved evidence citations
- Human approvals and rejections (with approver name and notes)
- Generated PDF paths and timestamps

### 7. Structured Output Only
All agents return verified JSON matching Pydantic schemas. No free-text prose responses. Benefits:
- Predictable frontend rendering
- Easy unit testing
- CMMS/MES integration-ready
- Prevents hallucinated prose being misinterpreted by operators

### 8. Apply All Memory Guardrails in Production

| Guardrail | Setting |
|---|---|
| Scanner batch cap | 2,000 tokens |
| KB context budget | 3,000 tokens |
| Scanner max_tokens | 800 |
| Investigator max_tokens | 1,500 |
| Technician max_tokens | 1,200 |
| PostgreSQL checkpointer | crash recovery + audit trail |
| Thread isolation | `thread_id = run_id` |
| UI buffer cap | 200 readings |
| Scoped Pinecone filter | by `line_id` |

---

## Demo Scenarios

| # | Scenario | Line | Trigger | Expected Verdict |
|---|---|---|---|---|
| 1 | Low pressure + output drop | LINE-B | `demo_scenario_line_b_pressure_drop()` | Stabilize |
| 2 | Temperature spike to 300°C | LINE-A | `TEMPERATURE_SPIKE` injection | Stabilize |
| 3 | Missing sensor data (DATA_GAP) | LINE-C | `DATA_GAP` injection | Investigate |
| 4 | High vibration trending up | LINE-C | `HIGH_VIBRATION` injection | Investigate |
| 5 | Repeated pressure pattern with history | LINE-B | Live stream with Pinecone history | Prevent Recurrence |

### Recommended Demo Walkthrough (Plant Manager)

1. Open dashboard → select `PLANT-01` / `LINE-B`
2. Select **Demo: LINE-B Pressure Drop** → click **Start Production Stream**
3. Scanner detects: `LOW_PRESSURE`, `OUTPUT_DROP`, `MISSING_SENSOR_DATA` — severity `HIGH`
4. Pipeline stepper: Scanner ✅ → Investigator 🔄 → Technician ⏳
5. Investigator retrieves `INC-2026-0312-LINE-B-004` + `MNT-2026-0428-009` from Pinecone
6. Verdict: **Stabilize** — 82% confidence, pressure valve actuator drift
7. Confidence breakdown bar shows 4 weighted components
8. Technician generates: shift handoff note + HIGH priority CMMS request + CAPA
9. Plant manager clicks **Approve** → approval written to audit_log
10. Plant manager downloads PDF corrective action plan

---

## Final Deliverables Checklist

### Engineering
- [ ] Vite + React + Shadcn/UI frontend with SSE consumer and approval UI
- [ ] FastAPI backend with all 6 API endpoints
- [ ] Sensor simulation service with 4 anomaly profiles and 4 named demo scenarios
- [ ] LangGraph multi-agent orchestration with PostgreSQL checkpointer
- [ ] Scanner Agent: prompt + rules JSON + output schema + token guardrail
- [ ] Investigator Agent: prompt + confidence schema + KB context budget
- [ ] Technician Agent: prompt + 4-section output schema + PDF trigger
- [ ] Pinecone ingestion pipeline (7 seeded documents)
- [ ] PostgreSQL schema (9 tables including audit_log)
- [ ] PDF generation with ReportLab (9 content sections)
- [ ] Docker Compose for full local stack (postgres + backend + frontend)
- [ ] `.env.example` with all required variables

### AI
- [ ] Scanner system prompt + anomaly rule JSON
- [ ] Investigator system prompt + weighted confidence schema
- [ ] Technician system prompt + CAPA output schema
- [ ] Pinecone seed script with metadata filter support
- [ ] Sample JSON: 2 prior incidents, 2 maintenance records, 3 SOP/standard chunks
- [ ] Evaluation examples for all 5 demo scenarios

### Business / Operations
- [ ] Demo scenario: LINE-B low pressure + output drop (primary demo)
- [ ] Demo scenario: temperature spike to 300°C
- [ ] Demo scenario: missing production data (DATA_GAP)
- [ ] PDF corrective action plan template (printable, CMMS-compatible)
- [ ] Shift handoff note template
- [ ] Maintenance request template (CMMS-ready fields)
- [ ] Approval workflow documentation for plant managers

---

## Definition of Done (per Phase)

### Phase 1 (MVP)
- All 3 agents produce valid JSON for the LINE-B pressure drop scenario
- PDF is generated and downloadable
- Human approval gate prevents CMMS action before `approved` status
- All memory guardrails active and tested
- `docker-compose up` boots the full stack from cold in < 60 seconds

### Phase 2
- Retrieval returns ≥3 relevant documents for each of the 5 demo scenarios
- Citation IDs appear in investigator output
- Hybrid search reduces irrelevant retrieval by measurable margin (A/B log)

### Phase 3
- Real CMMS ticket created post-approval in integration test environment
- Kafka consumer handles > 100 sensor events/second without queue backlog
- RBAC blocks non-supervisor users from approving CMMS escalations
