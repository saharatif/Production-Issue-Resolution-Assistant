# Module 1 Plan — Data Simulation & Frontend

## Goal
Build a fully self-contained data layer and frontend dashboard that lets a plant manager trigger simulated IoT sensor streams, observe live readings, and initiate the agent pipeline — all without a real plant connection.

---

## Deliverables

| # | Deliverable | Path |
|---|---|---|
| 1 | Sensor simulator service | `backend/app/services/simulation_service.py` |
| 2 | PostgreSQL seed script | `data/plant_history/seed.sql` |
| 3 | Pinecone seed script | `data/pinecone_seed/seed_pinecone.py` |
| 4 | Frontend Vite app (bootstrapped) | `frontend/` |
| 5 | SSE hook | `frontend/src/hooks/useSensorStream.ts` |
| 6 | TriggerButton component | `frontend/src/components/TriggerButton.tsx` |
| 7 | SensorStreamPanel component | `frontend/src/components/SensorStreamPanel.tsx` |
| 8 | ConfidenceBar component | `frontend/src/components/ConfidenceBar.tsx` |

---

## Step-by-Step Plan

### Step 1 — Bootstrap the Frontend
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npx shadcn@latest init
npm install tailwindcss @tailwindcss/vite lucide-react recharts
```
- Configure Tailwind in `vite.config.ts`
- Set up path alias `@/` → `src/`

### Step 2 — Build the Sensor Simulator
File: `backend/app/services/simulation_service.py`

- Define 4 production lines: `LINE-A`, `LINE-B`, `LINE-C`, `LINE-D`
- Define normal operating ranges for: `temperature_c`, `pressure_bar`, `vibration_mm_s`, `output_units_per_hour`
- Define 5 anomaly profiles: `LOW_PRESSURE`, `TEMPERATURE_SPIKE`, `HIGH_VIBRATION`, `OUTPUT_DROP`, `DATA_GAP`
- Implement `generate_batch(anomaly_probability=0.12)` — one reading per line per call
- Implement `generate_stream(interval_seconds=1.5)` — generator that yields batches
- Implement `demo_scenario_line_b_pressure_drop()` — deterministic demo for LINE-B

### Step 3 — Seed PostgreSQL
File: `data/plant_history/seed.sql`

Tables to populate:
- `plants` — PLANT-01 (Alpha Manufacturing, Dallas)
- `production_lines` — LINE-A through LINE-D
- `quality_thresholds` — warning and critical bounds per metric per line
- `maintenance_history` — 4 past maintenance events across LINE-A, LINE-B, LINE-C

### Step 4 — Seed Pinecone
File: `data/pinecone_seed/seed_pinecone.py`

Documents to embed and upsert (7 total):
- 2 prior incident reports (LINE-B pressure drop events)
- 2 maintenance records (PRESS-VALVE-23)
- 1 SOP — Pressure Control Procedure (LINE-B)
- 1 SOP — Thermal Anomaly Response
- 2 standards — ISO 9001:2015 Clause 8.5.1, ISO 13849 safety, OSHA 1910.147

Each vector must include metadata: `plant_id`, `line_id`, `machine_id`, `document_type`, `date`, `tags[]`

### Step 5 — SSE Hook
File: `frontend/src/hooks/useSensorStream.ts`

- Connect to `GET /stream/sensor?scenario=<scenario>` via `EventSource`
- Parse each `data:` event as a JSON array of `SensorReading`
- Prepend new readings to state, cap buffer at **200 entries** (memory guardrail)
- Expose `{ readings, connected }` to components

### Step 6 — TriggerButton Component
File: `frontend/src/components/TriggerButton.tsx`

- Scenario `<Select>`: Live Stream | Demo: LINE-B Pressure Drop | Demo: Temperature Spike | Demo: Missing Sensor Data
- Start / Stop toggle `<Button>` (green → red)
- Live/Offline `<Badge>` driven by `connected` from SSE hook

### Step 7 — SensorStreamPanel Component
File: `frontend/src/components/SensorStreamPanel.tsx`

- Render latest readings as a table: timestamp, line, machine, temperature, pressure, vibration, output, status
- Color-code rows: green = RUNNING, amber = WARNING, red = CRITICAL / DATA_GAP

### Step 8 — ConfidenceBar Component
File: `frontend/src/components/ConfidenceBar.tsx`

- Accept `breakdown: { historical_similarity, threshold_violation_strength, maintenance_history_match, data_completeness }`
- Render 4 labelled progress bars (blue fill, percentage label)

---

## Data Contracts

### SensorReading (TypeScript)
```typescript
interface SensorReading {
  timestamp:             string;
  plant_id:              string;
  line_id:               string;
  machine_id:            string;
  temperature_c:         number | null;
  pressure_bar:          number | null;
  vibration_mm_s:        number | null;
  output_units_per_hour: number | null;
  machine_status:        string;  // RUNNING | RUNNING_WITH_WARNING | CRITICAL_TEMPERATURE_SPIKE | DATA_GAP
}
```

### Anomaly Profiles (Python)
| Profile | Affected Metric | Range | Status |
|---|---|---|---|
| `LOW_PRESSURE` | `pressure_bar` | 0.05–0.15 bar | RUNNING_WITH_WARNING |
| `TEMPERATURE_SPIKE` | `temperature_c` | 280–320 °C | CRITICAL_TEMPERATURE_SPIKE |
| `HIGH_VIBRATION` | `vibration_mm_s` | 6.5–10.0 mm/s | RUNNING_WITH_WARNING |
| `OUTPUT_DROP` | `output_units_per_hour` | 200–450 units/hr | RUNNING_WITH_WARNING |
| `DATA_GAP` | all metrics | null | DATA_GAP |

---

## Acceptance Criteria

- [ ] `generate_batch()` returns 4 readings (one per line) and injects anomalies at ~12% probability
- [ ] `demo_scenario_line_b_pressure_drop()` always produces a LOW_PRESSURE reading on LINE-B
- [ ] Pinecone seed script runs without error and reports 7 documents upserted
- [ ] PostgreSQL seed script populates all 4 tables without constraint violations
- [ ] Frontend SSE hook connects and streams live data; badge shows "Live"
- [ ] Buffer never exceeds 200 readings in the UI state
- [ ] Scenario selector switches the SSE endpoint parameter correctly
- [ ] SensorStreamPanel highlights anomalous rows with correct colour

---

## Dependencies

- Python 3.12, FastAPI, `random`, `dataclasses`
- `pinecone`, `langchain_openai`, `openai` (for embeddings)
- `psycopg2` or `asyncpg` for PostgreSQL seed
- Node 20+, Vite 5, React 18, Shadcn/UI, Tailwind CSS 3, Recharts, Lucide React

---

## Environment Variables Required (this module)
```
# OPENAI_API_KEY is used for embedding generation in seed_pinecone.py
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=
DATABASE_URL=
```
