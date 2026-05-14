# Manufacturing: Production Issue Resolution Assistant
## Multi-Agent Implementation Guide — Final Version

> **Stack:** Vite · React · TypeScript · Shadcn/UI · Tailwind CSS · FastAPI · PostgreSQL · Pinecone · LangGraph · LangChain · OpenAI · ReportLab
>
> **Guardrails:** tiktoken batch trimming · per-agent max_tokens · KB context budget · LangGraph PostgreSQL checkpointer · thread-isolated concurrent runs · human-in-the-loop approval gates

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Module 1 — Data Simulation & Frontend](#module-1--data-simulation--frontend)
3. [Module 2 — Multi-Agent Architecture](#module-2--multi-agent-architecture)
4. [Module 3 — Technical Architecture & Implementation](#module-3--technical-architecture--implementation)
5. [Module 4 — Roadmap, Best Practices & Deliverables](#module-4--roadmap-best-practices--deliverables)

---

# 1. Project Overview

## Industry Problem

Manufacturing operations managers oversee multiple plants, production lines, machines, suppliers, and shifts. When something goes wrong, they need fast, reliable insight into root causes and immediate actions.

Typical production issues include:

- Quality defects or defect spikes
- Throughput or output drops
- Missing production data
- Supplier delivery delays
- Equipment downtime
- Abnormal IoT sensor readings (temperature, pressure, vibration, current spikes)
- Safety or compliance concerns

## Application Goal

A **multi-agent AI assistant** that accepts a short manufacturing problem statement, plant/line ID, timeframe, and optional logs, then produces a structured root-cause hypothesis, tiered recommendations, and an operator-ready next-step package.

## Example User Input

```json
{
  "problem_statement": "Output dropped on Line B and pressure sensor data is missing",
  "plant_id": "PLANT-01",
  "line_id": "LINE-B",
  "timeframe": "2026-05-14T06:00:00Z to 2026-05-14T10:00:00Z",
  "optional_notes": "Operator reported unstable pressure valve behavior during morning shift."
}
```

## Expected System Output

```json
{
  "issue_detected": true,
  "root_cause_hypothesis": [
    {
      "hypothesis": "Pressure valve actuator drift caused low pressure and reduced output.",
      "confidence": 0.82,
      "confidence_breakdown": {
        "historical_similarity": 0.35,
        "threshold_violation_strength": 0.25,
        "maintenance_history_match": 0.25,
        "data_completeness": 0.15
      },
      "evidence": [
        "Pressure dropped below minimum threshold for 18 minutes.",
        "Identical incident on LINE-B in March 2026 resolved by valve tuning.",
        "Maintenance record from April 2026 noted actuator response delay."
      ]
    }
  ],
  "recommendations": {
    "stabilize": [
      "Switch Line B to controlled low-speed mode.",
      "Inspect pressure valve actuator.",
      "Notify shift supervisor and maintenance team."
    ],
    "investigate": [
      "Review pressure sensor logs for missing or flatlined values.",
      "Check maintenance history for repeated valve-tuning issues."
    ],
    "prevent_recurrence": [
      "Add automated alert for pressure drift below threshold.",
      "Schedule preventive maintenance for valve calibration."
    ]
  },
  "next_step_package": {
    "shift_handoff_note": "Line B experienced low pressure and reduced output during the morning shift. Maintenance inspection required before returning to full speed.",
    "maintenance_request": "Inspect and tune pressure valve actuator on LINE-B. Verify pressure sensor signal integrity.",
    "corrective_action_plan_summary": "Stabilize production, inspect valve and sensor health, then implement alerting and preventive maintenance.",
    "supplier_questions": []
  }
}
```

---

# Module 1 — Data Simulation & Frontend

## 1.1 Objective

Create simulated manufacturing data representing production line behavior, equipment conditions, and IoT sensor signals. This module allows full system testing without a live plant connection.

## 1.2 Input Data Types

The system simulates or accepts:

- Temperature sensor readings (°C)
- Pressure sensor readings (bar)
- Vibration data (mm/s RMS)
- Throughput / output count (units/hour)
- Machine status codes
- Downtime events
- Missing sensor readings (null values)
- Operator notes
- Maintenance logs
- Prior incident records
- Quality inspection results

## 1.3 Example Simulated Sensor Data

```json
[
  {
    "timestamp": "2026-05-14T08:00:00Z",
    "plant_id": "PLANT-01",
    "line_id": "LINE-B",
    "machine_id": "PRESS-VALVE-23",
    "temperature_c": 72.4,
    "pressure_bar": 5.8,
    "vibration_mm_s": 2.1,
    "output_units_per_hour": 950,
    "machine_status": "RUNNING"
  },
  {
    "timestamp": "2026-05-14T08:15:00Z",
    "plant_id": "PLANT-01",
    "line_id": "LINE-B",
    "machine_id": "PRESS-VALVE-23",
    "temperature_c": 76.8,
    "pressure_bar": 0.08,
    "vibration_mm_s": 2.3,
    "output_units_per_hour": 610,
    "machine_status": "RUNNING_WITH_WARNING"
  },
  {
    "timestamp": "2026-05-14T08:30:00Z",
    "plant_id": "PLANT-01",
    "line_id": "LINE-B",
    "machine_id": "PRESS-VALVE-23",
    "temperature_c": null,
    "pressure_bar": null,
    "vibration_mm_s": 2.4,
    "output_units_per_hour": 520,
    "machine_status": "DATA_GAP"
  }
]
```

## 1.4 Python Sensor Simulator — `backend/app/services/simulation_service.py`

```python
import random
import json
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict, field
from typing import Generator

# ── Production Lines ────────────────────────────────────────────────────────
LINES = [
    {"plant_id": "PLANT-01", "line_id": "LINE-A", "machine_id": "CNC-MILL-11"},
    {"plant_id": "PLANT-01", "line_id": "LINE-B", "machine_id": "PRESS-VALVE-23"},
    {"plant_id": "PLANT-01", "line_id": "LINE-C", "machine_id": "SPINDLE-07"},
    {"plant_id": "PLANT-01", "line_id": "LINE-D", "machine_id": "COAT-SPRAY-04"},
]

# ── Normal Operating Ranges ─────────────────────────────────────────────────
NORMAL = {
    "temperature_c":          (68.0, 82.0),
    "pressure_bar":           (5.2, 6.2),
    "vibration_mm_s":         (1.5, 2.8),
    "output_units_per_hour":  (900, 1050),
}

# ── Anomaly Injection Profiles ──────────────────────────────────────────────
ANOMALY_PROFILES = {
    "LOW_PRESSURE": {
        "pressure_bar": (0.05, 0.15),
        "output_units_per_hour": (450, 650),
        "machine_status": "RUNNING_WITH_WARNING",
    },
    "TEMPERATURE_SPIKE": {
        "temperature_c": (280, 320),
        "output_units_per_hour": (300, 500),
        "machine_status": "CRITICAL_TEMPERATURE_SPIKE",
    },
    "HIGH_VIBRATION": {
        "vibration_mm_s": (6.5, 10.0),
        "machine_status": "RUNNING_WITH_WARNING",
    },
    "OUTPUT_DROP": {
        "output_units_per_hour": (200, 450),
        "machine_status": "RUNNING_WITH_WARNING",
    },
    "DATA_GAP": None,   # Signals a dropped packet (all metrics → null)
}

@dataclass
class SensorReading:
    timestamp:              str
    plant_id:               str
    line_id:                str
    machine_id:             str
    temperature_c:          float | None
    pressure_bar:           float | None
    vibration_mm_s:         float | None
    output_units_per_hour:  int | None
    machine_status:         str
    _anomaly_tag:           str | None = field(default=None, repr=False)

def _normal(line: dict) -> SensorReading:
    return SensorReading(
        timestamp             = datetime.now(timezone.utc).isoformat(),
        plant_id              = line["plant_id"],
        line_id               = line["line_id"],
        machine_id            = line["machine_id"],
        temperature_c         = round(random.uniform(*NORMAL["temperature_c"]), 2),
        pressure_bar          = round(random.uniform(*NORMAL["pressure_bar"]), 2),
        vibration_mm_s        = round(random.uniform(*NORMAL["vibration_mm_s"]), 2),
        output_units_per_hour = random.randint(*NORMAL["output_units_per_hour"]),
        machine_status        = "RUNNING",
    )

def _inject(r: SensorReading, tag: str) -> SensorReading:
    profile = ANOMALY_PROFILES[tag]
    if profile is None:
        r.temperature_c         = None
        r.pressure_bar          = None
        r.vibration_mm_s        = None
        r.output_units_per_hour = None
        r.machine_status        = "DATA_GAP"
        r._anomaly_tag          = "DATA_GAP"
        return r
    for key, val in profile.items():
        if key == "machine_status":
            r.machine_status = val
        elif isinstance(val, tuple) and isinstance(val[0], float):
            setattr(r, key, round(random.uniform(*val), 3))
        elif isinstance(val, tuple):
            setattr(r, key, random.randint(*val))
    r._anomaly_tag = tag
    return r

def generate_batch(anomaly_probability: float = 0.12) -> list[dict]:
    batch = []
    for line in LINES:
        r = _normal(line)
        if random.random() < anomaly_probability:
            tag = random.choice(list(ANOMALY_PROFILES.keys()))
            r   = _inject(r, tag)
        d = asdict(r)
        d.pop("_anomaly_tag", None)   # strip internal label before sending to UI
        batch.append(d)
    return batch

def generate_stream(
    interval_seconds: float = 1.5,
    anomaly_probability: float = 0.12,
) -> Generator[list[dict], None, None]:
    import time
    while True:
        yield generate_batch(anomaly_probability)
        time.sleep(interval_seconds)

# ── Named Demo Scenarios ────────────────────────────────────────────────────
def demo_scenario_line_b_pressure_drop() -> list[dict]:
    """
    Deterministic demo: LINE-B shows low pressure + output drop + data gap.
    Used for the recommended demo story in Module 4.
    """
    base = generate_batch(anomaly_probability=0)
    for r in base:
        if r["line_id"] == "LINE-B":
            r["pressure_bar"]          = round(random.uniform(0.05, 0.12), 3)
            r["output_units_per_hour"] = random.randint(450, 620)
            r["machine_status"]        = "RUNNING_WITH_WARNING"
    return base
```

## 1.5 Seed Data — PostgreSQL & Pinecone

### 1.5.1 Relational Seed — `data/plant_history/seed.sql`

```sql
-- Plants
INSERT INTO plants (id, name, location, timezone) VALUES
  ('PLANT-01', 'Alpha Manufacturing – Dallas', 'Dallas, TX', 'America/Chicago');

-- Production Lines
INSERT INTO production_lines (id, plant_id, name, product_type) VALUES
  ('LINE-A', 'PLANT-01', 'CNC Milling A',      'Precision Shafts'),
  ('LINE-B', 'PLANT-01', 'Hydraulic Press B',  'Automotive Body Panels'),
  ('LINE-C', 'PLANT-01', 'Spindle Machining C','Gear Components'),
  ('LINE-D', 'PLANT-01', 'Paint & Coating D',  'Surface Finishing');

-- Quality Thresholds (per line per metric)
INSERT INTO quality_thresholds
  (line_id, metric, warning_low, warning_high, critical_low, critical_high, unit)
VALUES
  ('LINE-B', 'temperature_c',         65.0,   90.0,  55.0,  150.0, '°C'),
  ('LINE-B', 'pressure_bar',           4.8,    6.5,   3.5,    8.0, 'bar'),
  ('LINE-B', 'vibration_mm_s',         1.0,    4.0,   0.5,    8.0, 'mm/s'),
  ('LINE-B', 'output_units_per_hour', 700.0, 1100.0, 500.0, 1200.0, 'units/hr');

-- Maintenance History
INSERT INTO maintenance_history
  (line_id, machine_id, event_date, event_type, description, resolved_by, resolution_note)
VALUES
  ('LINE-B', 'PRESS-VALVE-23', '2026-03-12', 'corrective',
   'Pressure dropped below operating threshold. Output decreased 38%.',
   'Tech: Technician A',
   'Pressure valve recalibrated and actuator response verified. Output restored within 2 hours.'),

  ('LINE-B', 'PRESS-VALVE-23', '2026-04-28', 'preventive',
   'Minor actuator response delay observed during pressure ramp test.',
   'Tech: Technician A',
   'Valve cleaned and response tested. Follow-up calibration recommended at next planned downtime.'),

  ('LINE-A', 'CNC-MILL-11', '2026-01-05', 'corrective',
   'Temperature spike to 295°C on roller bearing housing. Lubrication line blocked.',
   'Tech: Technician B',
   'Purged lubrication line. Replaced bearing assembly. Temperature back to 72°C nominal.'),

  ('LINE-C', 'SPINDLE-07', '2026-03-18', 'preventive',
   'Scheduled vibration analysis found early-stage bearing degradation at spindle motor 2.',
   'Tech: Technician C',
   'Pre-emptive bearing swap. Zero downtime impact.');
```

### 1.5.2 Pinecone Seed — `data/pinecone_seed/seed_pinecone.py`

```python
"""
Seeds Pinecone with incident reports, maintenance records, SOPs, and regulatory excerpts.
Run once:  python data/pinecone_seed/seed_pinecone.py
"""

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
import os, json

pc  = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
emb = OpenAIEmbeddings(model="text-embedding-3-small")
IDX = "manufacturing-kb"

if IDX not in [i.name for i in pc.list_indexes()]:
    pc.create_index(IDX, dimension=1536, metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"))

index = pc.Index(IDX)

DOCUMENTS = [
    # ── Prior Incidents ─────────────────────────────────────────────────────
    {
        "id": "INC-2026-0312-LINE-B-004",
        "text": (
            "Incident INC-2026-0312-LINE-B-004. PLANT-01, LINE-B, PRESS-VALVE-23. "
            "Date: 2026-03-12. Type: LOW_PRESSURE_OUTPUT_DROP. "
            "Description: Pressure dropped below operating threshold and production output decreased by 38%. "
            "Root cause: Pressure valve actuator drift after extended runtime. "
            "Corrective action: Pressure valve recalibrated, actuator response verified. "
            "Preventive action: Added weekly pressure valve calibration check. "
            "Outcome: Line returned to normal output after valve tuning."
        ),
        "metadata": {
            "plant_id": "PLANT-01", "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23", "document_type": "incident_report",
            "date": "2026-03-12",
            "tags": ["pressure", "output_drop", "valve_tuning", "LINE-B"],
        },
    },
    {
        "id": "MNT-2026-0428-009",
        "text": (
            "Maintenance record MNT-2026-0428-009. Machine: PRESS-VALVE-23, LINE-B. "
            "Type: PREVENTIVE. Date: 2026-04-28. Technician: Technician A. "
            "Finding: Minor actuator response delay observed during pressure ramp test. "
            "Action: Valve cleaned and response tested. "
            "Follow-up required: Yes. Recommendation: Repeat calibration at next planned downtime."
        ),
        "metadata": {
            "plant_id": "PLANT-01", "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23", "document_type": "maintenance_record",
            "date": "2026-04-28",
            "tags": ["pressure", "valve", "calibration", "preventive"],
        },
    },
    # ── SOPs ────────────────────────────────────────────────────────────────
    {
        "id": "SOP-LINE-B-PRESSURE-001",
        "text": (
            "SOP-LINE-B-PRESSURE-001 – Pressure Control Procedure for Line B. Revision 1.2. "
            "If pressure drops below 4.8 bar (minimum operating threshold): "
            "Step 1 – Reduce line speed to 30%. "
            "Step 2 – Inspect pressure valve actuator and hydraulic fluid level. "
            "Step 3 – Verify sensor signal integrity. "
            "Step 4 – If pressure < 3.5 bar, initiate immediate line stop. "
            "Step 5 – Notify maintenance before returning to full-speed operation. "
            "Minimum pressure: 4.8 bar. Related metrics: pressure_bar, output_units_per_hour."
        ),
        "metadata": {
            "plant_id": "PLANT-01", "line_id": "LINE-B",
            "document_type": "SOP", "tags": ["pressure", "valve", "procedure"],
        },
    },
    {
        "id": "SOP-THERM-001",
        "text": (
            "SOP-THERM-001 – Thermal Anomaly Response. "
            "If temperature exceeds 90°C (warning): reduce throughput 50% and inspect bearing lubrication. "
            "If temperature exceeds 150°C (critical): stop line immediately, isolate heat source. "
            "Notify shift supervisor within 5 minutes. Apply LOTO before inspection. "
            "Check lubrication system, cooling water flow, and bearing housing first."
        ),
        "metadata": {
            "document_type": "SOP", "tags": ["temperature", "bearing", "thermal"],
        },
    },
    # ── ISO / Regulatory ────────────────────────────────────────────────────
    {
        "id": "ISO-9001-8-5-1",
        "text": (
            "ISO 9001:2015 Clause 8.5.1 – Control of production and service provision. "
            "The organization shall implement production under controlled conditions including "
            "monitoring and measurement at appropriate stages to verify that process control "
            "criteria have been met. Out-of-range sensor readings must be logged and investigated "
            "within one shift cycle. Corrective actions must be documented with evidence."
        ),
        "metadata": {
            "document_type": "standard", "source": "ISO_9001", "tags": ["iso", "quality"],
        },
    },
    {
        "id": "ISO-13849-SAFETY",
        "text": (
            "ISO 13849-1:2015 – Safety of machinery. "
            "When a safety-related control system detects an abnormal parameter "
            "(temperature > 150°C or pressure > 8 bar for Category 3 lines), "
            "an automatic safe-state initiation is required. "
            "Manual restart must only occur after a qualified technician signs off on root-cause verification. "
            "Lock-out/tag-out (LOTO) procedures per OSHA 1910.147 apply before corrective maintenance."
        ),
        "metadata": {
            "document_type": "standard", "source": "ISO_13849",
            "tags": ["safety", "loto", "critical"],
        },
    },
    {
        "id": "OSHA-1910-147",
        "text": (
            "OSHA 29 CFR 1910.147 – Control of Hazardous Energy (Lockout/Tagout). "
            "Before any employee performs servicing or maintenance where unexpected energization "
            "could cause injury, the machine must be isolated from energy sources and locked out. "
            "Each authorized employee applies their own lock. "
            "Verification of de-energization must be confirmed before work begins."
        ),
        "metadata": {
            "document_type": "regulation", "source": "OSHA",
            "tags": ["loto", "safety", "lockout"],
        },
    },
]

vectors = []
for doc in DOCUMENTS:
    vec = emb.embed_query(doc["text"])
    vectors.append({
        "id": doc["id"],
        "values": vec,
        "metadata": {"text": doc["text"], **doc["metadata"]},
    })

index.upsert(vectors=vectors)
print(f"Seeded {len(vectors)} documents into Pinecone index '{IDX}'.")
```

## 1.6 Frontend — Vite + React + Shadcn/UI

### Bootstrap

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npx shadcn@latest init
npm install tailwindcss @tailwindcss/vite lucide-react recharts
```

### Directory Structure

```
frontend/src/
├── components/
│   ├── TriggerButton.tsx          # Start/Stop stream + scenario selector
│   ├── SensorStreamPanel.tsx      # Live sensor table with severity highlighting
│   ├── AgentPipelineStatus.tsx    # Scanner → Investigator → Technician stepper
│   ├── AlertCard.tsx              # Scanner anomaly alert card
│   ├── InvestigatorReport.tsx     # Verdict banner + root-cause hypotheses
│   ├── ConfidenceBar.tsx          # Weighted breakdown visualizer
│   ├── ActionPlanPanel.tsx        # Tiered recommendations + next-step package
│   └── ApprovalGate.tsx           # Human-in-the-loop approval UI (Phase 2)
├── hooks/
│   ├── useSensorStream.ts         # SSE consumer with 200-reading buffer cap
│   └── useAgentPipeline.ts        # Pipeline trigger + status polling
├── lib/
│   └── api.ts                     # Typed FastAPI client
└── App.tsx
```

### `src/hooks/useSensorStream.ts`

```typescript
import { useState, useEffect, useRef } from "react";

export interface SensorReading {
  timestamp:             string;
  plant_id:              string;
  line_id:               string;
  machine_id:            string;
  temperature_c:         number | null;
  pressure_bar:          number | null;
  vibration_mm_s:        number | null;
  output_units_per_hour: number | null;
  machine_status:        string;
}

const BUFFER_CAP = 200;   // ← Memory guardrail: prevents unbounded UI list growth

export function useSensorStream(active: boolean) {
  const [readings, setReadings] = useState<SensorReading[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!active) { esRef.current?.close(); setConnected(false); return; }

    const es = new EventSource("http://localhost:8000/stream/sensor");
    esRef.current = es;
    es.onopen    = () => setConnected(true);
    es.onerror   = () => setConnected(false);
    es.onmessage = (e) => {
      const batch: SensorReading[] = JSON.parse(e.data);
      setReadings((prev) => [...batch, ...prev].slice(0, BUFFER_CAP));
    };

    return () => { es.close(); setConnected(false); };
  }, [active]);

  return { readings, connected };
}
```

### `src/components/TriggerButton.tsx`

```tsx
import { Button } from "@/components/ui/button";
import { Badge }  from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue }
  from "@/components/ui/select";
import { Wifi, WifiOff, Zap } from "lucide-react";

export type DemoScenario = "live" | "pressure_drop" | "temp_spike" | "data_gap";

interface Props {
  active:    boolean;
  connected: boolean;
  scenario:  DemoScenario;
  onToggle:  () => void;
  onScenario: (s: DemoScenario) => void;
}

export function TriggerButton({ active, connected, scenario, onToggle, onScenario }: Props) {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      <Select value={scenario} onValueChange={(v) => onScenario(v as DemoScenario)}>
        <SelectTrigger className="w-52">
          <SelectValue placeholder="Select scenario" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="live">Live Stream</SelectItem>
          <SelectItem value="pressure_drop">Demo: LINE-B Pressure Drop</SelectItem>
          <SelectItem value="temp_spike">Demo: Temperature Spike 300°C</SelectItem>
          <SelectItem value="data_gap">Demo: Missing Sensor Data</SelectItem>
        </SelectContent>
      </Select>

      <Button
        size="lg"
        variant={active ? "destructive" : "default"}
        onClick={onToggle}
        className="gap-2 font-semibold"
      >
        <Zap className="h-4 w-4" />
        {active ? "Stop Stream" : "Start Production Stream"}
      </Button>

      <Badge variant={connected ? "default" : "secondary"} className="gap-1">
        {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
        {connected ? "Live" : "Offline"}
      </Badge>
    </div>
  );
}
```

### `src/components/ConfidenceBar.tsx`

```tsx
interface Breakdown {
  historical_similarity:        number;
  threshold_violation_strength: number;
  maintenance_history_match:    number;
  data_completeness:            number;
}

const LABELS: Record<keyof Breakdown, string> = {
  historical_similarity:        "Historical Match",
  threshold_violation_strength: "Threshold Severity",
  maintenance_history_match:    "Maintenance Records",
  data_completeness:            "Data Completeness",
};

export function ConfidenceBar({ breakdown }: { breakdown: Breakdown }) {
  return (
    <div className="space-y-1 text-xs">
      {(Object.keys(breakdown) as (keyof Breakdown)[]).map((k) => (
        <div key={k} className="flex items-center gap-2">
          <span className="w-40 text-muted-foreground">{LABELS[k]}</span>
          <div className="flex-1 bg-muted rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${breakdown[k] * 100}%` }}
            />
          </div>
          <span className="w-8 text-right">{Math.round(breakdown[k] * 100)}%</span>
        </div>
      ))}
    </div>
  );
}
```

---

# Module 2 — Multi-Agent Architecture

## 2.1 Agent Pipeline Overview

```
 ┌─────────────────┐
 │   START (batch) │
 └────────┬────────┘
          │
          ▼
 ┌──────────────────┐    No anomaly
 │  Agent 1:        │ ──────────────────────► END  (clean batch logged)
 │  SCANNER         │
 └────────┬─────────┘
          │ anomaly_detected = true
          ▼
 ┌──────────────────┐
 │  Agent 2:        │  ← queries Pinecone KB, PostgreSQL history
 │  INVESTIGATOR    │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐
 │  Agent 3:        │  ← generates operational documents + PDF
 │  PLANT           │
 │  TECHNICIAN      │
 └────────┬─────────┘
          │
          ▼
 ┌──────────────────┐
 │  HUMAN APPROVAL  │  ← required before creating CMMS tickets or notifying suppliers
 │  GATE            │
 └──────────────────┘
```

## 2.2 LangGraph State

```python
# backend/app/workflows/manufacturing_graph.py

from typing import TypedDict, Optional, List, Dict, Any

class ManufacturingIssueState(TypedDict):
    run_id:               str
    problem_statement:    str
    plant_id:             str
    line_id:              str
    timeframe_start:      str
    timeframe_end:        str
    raw_sensor_data:      List[Dict[str, Any]]
    scanner_result:       Optional[Dict[str, Any]]
    retrieved_context:    Optional[List[Dict[str, Any]]]
    investigator_result:  Optional[Dict[str, Any]]
    technician_result:    Optional[Dict[str, Any]]
    approval_status:      str          # "pending" | "approved" | "rejected"
    final_report_path:    Optional[str]
    has_anomaly:          bool
```

## 2.3 Agent 1 — Scanner Agent

### Role
Reads incoming production data, applies threshold rules, detects anomalies, and emits a structured alert. Uses pure Python for clean batches (zero LLM cost). Calls LLM only when rule-based detection flags an event.

### Scanner Rules JSON — `data/scanner_rules.json`

```json
{
  "rules": [
    {
      "metric": "temperature_c",
      "condition": ">",
      "threshold": 90,
      "critical_threshold": 150,
      "severity": "HIGH",
      "anomaly_type": "TEMPERATURE_SPIKE"
    },
    {
      "metric": "pressure_bar",
      "condition": "<",
      "threshold": 4.8,
      "critical_threshold": 3.5,
      "severity": "HIGH",
      "anomaly_type": "LOW_PRESSURE"
    },
    {
      "metric": "vibration_mm_s",
      "condition": ">",
      "threshold": 4.0,
      "critical_threshold": 8.0,
      "severity": "MEDIUM",
      "anomaly_type": "HIGH_VIBRATION"
    },
    {
      "metric": "output_units_per_hour",
      "condition": "<",
      "threshold": 700,
      "critical_threshold": 500,
      "severity": "MEDIUM",
      "anomaly_type": "OUTPUT_DROP"
    },
    {
      "metric": "pressure_bar",
      "condition": "is_null",
      "severity": "HIGH",
      "anomaly_type": "MISSING_SENSOR_DATA"
    },
    {
      "metric": "temperature_c",
      "condition": "is_null",
      "severity": "HIGH",
      "anomaly_type": "MISSING_SENSOR_DATA"
    }
  ]
}
```

### Scanner Output Schema

```json
{
  "scanner_agent_output": {
    "anomaly_detected": true,
    "plant_id": "PLANT-01",
    "line_id": "LINE-B",
    "machine_id": "PRESS-VALVE-23",
    "anomaly_type": ["LOW_PRESSURE", "OUTPUT_DROP", "MISSING_SENSOR_DATA"],
    "severity": "HIGH",
    "details": [
      "Pressure dropped to 0.08 bar — below minimum threshold of 4.8 bar.",
      "Output dropped from expected 950 units/hour to 520 units/hour.",
      "Temperature and pressure readings missing at timestamp 2026-05-14T08:30:00Z."
    ],
    "recommended_next_agent": "Investigator Agent"
  }
}
```

### Implementation — `backend/app/agents/scanner_agent.py`

```python
import json, tiktoken
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import settings

# ── Memory Guardrail: token budget for incoming batch ──────────────────────
MAX_BATCH_TOKENS = 2000

def _trim_batch(batch: list[dict]) -> list[dict]:
    """
    Trim sensor batch to MAX_BATCH_TOKENS before sending to LLM.
    Prioritises most-recent readings (head of list).
    """
    enc     = tiktoken.encoding_for_model("gpt-4o")
    result, total = [], 0
    for reading in batch:
        chunk  = json.dumps(reading)
        tokens = len(enc.encode(chunk))
        if total + tokens > MAX_BATCH_TOKENS:
            break
        result.append(reading)
        total += tokens
    return result

# ── LLM: temperature=0, max_tokens enforced ───────────────────────────────
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=800,           # ← Memory guardrail: scanner output is short/structured
    openai_api_key=settings.openai_api_key,
)

SCANNER_SYSTEM = """
You are the SCANNER agent for a manufacturing plant monitoring system.

Rules for anomaly detection:
- TEMPERATURE_SPIKE : temperature_c > 90°C (critical > 150°C)
- LOW_PRESSURE      : pressure_bar < 4.8 bar (critical < 3.5 bar)
- HIGH_VIBRATION    : vibration_mm_s > 4.0 (critical > 8.0)
- OUTPUT_DROP       : output_units_per_hour < 700 (critical < 500)
- MISSING_DATA      : any key metric is null

Severity:
- "CRITICAL" : value outside critical bounds OR metric is null
- "HIGH"     : value outside normal bounds but within critical
- "MEDIUM"   : minor deviation worth logging
- "NONE"     : all metrics normal

Return STRICT JSON only (no markdown, no preamble):
{
  "anomaly_detected": true,
  "plant_id": "...",
  "line_id": "...",
  "machine_id": "...",
  "anomaly_type": ["LOW_PRESSURE", "OUTPUT_DROP"],
  "severity": "HIGH",
  "details": ["...", "..."],
  "recommended_next_agent": "Investigator Agent"
}

If no anomaly: return {"anomaly_detected": false, "severity": "NONE", "details": []}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SCANNER_SYSTEM),
    ("human",  "Sensor batch:\n{sensor_batch}\n\nAnalyse and return the JSON report."),
])

def _parse_json(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1][4:] if parts[1].startswith("json") else parts[1]
    return json.loads(content.strip())

async def scanner_node(state: dict) -> dict:
    trimmed_batch = _trim_batch(state["raw_sensor_data"])   # ← guardrail applied
    chain         = prompt | llm
    response      = await chain.ainvoke({"sensor_batch": json.dumps(trimmed_batch, indent=2)})
    result        = _parse_json(response.content)
    return {
        **state,
        "scanner_result": result,
        "has_anomaly":    result.get("anomaly_detected", False),
    }
```

## 2.4 Agent 2 — Investigator Agent

### Role
Performs root-cause analysis using Pinecone RAG, PostgreSQL history, SOPs, safety standards, and prior incident patterns. Produces a verdict with weighted confidence and tiered recommendations.

### Investigator Input Context Examples

**Prior Incident JSON** (stored in Pinecone, also `data/prior_incidents/`)

```json
{
  "incident_id": "INC-2026-0312-LINE-B-004",
  "plant_id": "PLANT-01",
  "line_id": "LINE-B",
  "machine_id": "PRESS-VALVE-23",
  "incident_type": "LOW_PRESSURE_OUTPUT_DROP",
  "date": "2026-03-12",
  "description": "Pressure dropped below operating threshold and production output decreased by 38%.",
  "root_cause": "Pressure valve actuator drift after extended runtime.",
  "corrective_action": "Pressure valve recalibrated and actuator response verified.",
  "preventive_action": "Added weekly pressure valve calibration check.",
  "outcome": "Line returned to normal output after valve tuning.",
  "tags": ["pressure", "output_drop", "valve_tuning", "LINE-B"]
}
```

**Maintenance Record JSON** (stored in Pinecone, also `data/maintenance_records/`)

```json
{
  "maintenance_record_id": "MNT-2026-0428-009",
  "machine_id": "PRESS-VALVE-23",
  "line_id": "LINE-B",
  "maintenance_type": "PREVENTIVE",
  "performed_on": "2026-04-28",
  "technician": "Technician A",
  "finding": "Minor actuator response delay observed during pressure ramp test.",
  "action_taken": "Valve cleaned and response tested.",
  "follow_up_required": true,
  "recommended_follow_up": "Repeat calibration during next planned downtime."
}
```

**SOP Chunk JSON** (stored in Pinecone, also `data/sop_documents/`)

```json
{
  "document_id": "SOP-LINE-B-PRESSURE-001",
  "document_type": "SOP",
  "title": "Pressure Control Procedure for Line B",
  "content": "If pressure drops below 4.8 bar, reduce production speed, inspect pressure valve actuator, verify sensor signal integrity, and notify maintenance before returning to full-speed operation.",
  "related_metrics": ["pressure_bar", "output_units_per_hour"],
  "minimum_pressure_bar": 4.8,
  "revision": "1.2"
}
```

### Investigator Output Schema

```json
{
  "investigator_agent_output": {
    "verdict": "Stabilize",
    "root_cause_hypotheses": [
      {
        "hypothesis": "Pressure valve actuator drift caused low pressure and output drop.",
        "confidence": 0.82,
        "confidence_breakdown": {
          "historical_similarity": 0.35,
          "threshold_violation_strength": 0.25,
          "maintenance_history_match": 0.25,
          "data_completeness": 0.15
        },
        "supporting_evidence": [
          "Pressure dropped to 0.08 bar — current threshold is 4.8 bar.",
          "Incident INC-2026-0312-LINE-B-004 was resolved by pressure valve tuning.",
          "Maintenance record MNT-2026-0428-009 reported actuator response delay."
        ]
      },
      {
        "hypothesis": "Pressure sensor signal failure caused unreliable process control.",
        "confidence": 0.64,
        "confidence_breakdown": {
          "historical_similarity": 0.20,
          "threshold_violation_strength": 0.20,
          "maintenance_history_match": 0.10,
          "data_completeness": 0.14
        },
        "supporting_evidence": [
          "Temperature and pressure values were null at one timestamp.",
          "Machine status changed to DATA_GAP."
        ]
      }
    ],
    "recommendations": {
      "stabilize": [
        "Reduce line speed or pause production if pressure remains below 4.8 bar.",
        "Inspect pressure valve actuator immediately.",
        "Verify pressure sensor connectivity and signal quality."
      ],
      "investigate": [
        "Compare current pressure trend with March 2026 incident.",
        "Review calibration records for PRESS-VALVE-23.",
        "Check whether the weekly valve calibration was completed."
      ],
      "prevent_recurrence": [
        "Add automated pressure drift alerting at 5.0 bar early-warning threshold.",
        "Update PM checklist to include actuator response verification.",
        "Create recurring trend review for pressure-control equipment on Line B."
      ]
    },
    "compliance_reference": [
      "Follow SOP-LINE-B-PRESSURE-001 for low-pressure response procedure.",
      "ISO 9001:2015 Clause 8.5.1 requires logging and investigation within one shift.",
      "Escalate immediately if pressure breaches critical threshold of 3.5 bar."
    ]
  }
}
```

### Implementation — `backend/app/agents/investigator_agent.py`

```python
import json, tiktoken
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import settings
from services.pinecone_service import retrieve_similar

# ── Memory Guardrail: KB context token budget ──────────────────────────────
MAX_KB_TOKENS = 3000

def _build_kb_context(anomalies: list[dict], line_id: str) -> str:
    enc  = tiktoken.encoding_for_model("gpt-4o")
    seen, chunks, total = set(), [], 0

    for a in anomalies:
        query = f"{a.get('anomaly_type', '')} on {line_id} — {' '.join(a.get('details', []))}"
        hits  = retrieve_similar(
            query,
            top_k=4,
            filter_meta={"line_id": {"$eq": line_id}},   # scoped retrieval
        )
        for h in hits:
            if h["text"] in seen:
                continue
            cost = len(enc.encode(h["text"]))
            if total + cost > MAX_KB_TOKENS:
                break                                      # ← hard token ceiling
            seen.add(h["text"])
            chunks.append(f"[{h['source']} | relevance={h['score']:.2f}]\n{h['text']}")
            total += cost

    return "\n\n".join(chunks) or "No matching records in knowledge base."

# ── LLM: max_tokens enforced ──────────────────────────────────────────────
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    max_tokens=1500,          # ← Memory guardrail
    openai_api_key=settings.openai_api_key,
)

INVESTIGATOR_SYSTEM = """
You are the INVESTIGATOR agent in a manufacturing issue resolution system.
You receive: (1) scanner anomaly details, (2) retrieved knowledge-base context.

Your responsibilities:
1. Identify the most likely root cause(s) with a weighted confidence breakdown.
2. Issue a verdict: "Stabilize", "Investigate", or "Prevent Recurrence".
3. Provide tiered recommendations (stabilize / investigate / prevent_recurrence).
4. Cite referenced standards, SOPs, and prior incidents.

Verdict guide:
- "Stabilize"          → Immediate risk to people, equipment, or production. Act NOW.
- "Investigate"        → Anomaly is significant but not immediately dangerous.
- "Prevent Recurrence" → Pattern has occurred before; systemic fix is needed.

Confidence breakdown weights (must sum to 1.0):
  historical_similarity        : 0.35
  threshold_violation_strength : 0.25
  maintenance_history_match    : 0.25
  data_completeness            : 0.15

Return STRICT JSON only (no markdown):
{
  "verdict": "...",
  "root_cause_hypotheses": [...],
  "recommendations": {"stabilize": [...], "investigate": [...], "prevent_recurrence": [...]},
  "compliance_reference": [...]
}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", INVESTIGATOR_SYSTEM),
    ("human",  "ANOMALIES:\n{anomalies}\n\nKNOWLEDGE BASE:\n{kb_context}\n\nReturn verdict JSON."),
])

async def investigator_node(state: dict) -> dict:
    scanner   = state["scanner_result"]
    anomalies = [scanner]   # scanner_result is a single structured dict
    kb        = _build_kb_context(anomalies, state["line_id"])

    chain    = prompt | llm
    response = await chain.ainvoke({
        "anomalies":  json.dumps(scanner, indent=2),
        "kb_context": kb,
    })

    content = response.content.strip()
    if content.startswith("```"):
        parts   = content.split("```")
        content = parts[1][4:] if parts[1].startswith("json") else parts[1]

    result = json.loads(content.strip())
    return {
        **state,
        "retrieved_context":   kb,
        "investigator_result": result,
    }
```

## 2.5 Agent 3 — Plant Technician Agent

### Role
Converts the investigator verdict into operator-ready documentation: shift handoff note, CMMS maintenance request, corrective action plan (CAPA), and supplier questions. Then generates a PDF report.

### Technician Output Schema

```json
{
  "plant_technician_agent_output": {
    "shift_handoff_note": {
      "title": "Shift Handoff: Line B Low Pressure and Output Drop",
      "summary": "Line B experienced low pressure, missing sensor data, and reduced output during the morning shift.",
      "current_status": "Line should remain in controlled low-speed operation until valve and sensor checks are completed.",
      "actions_completed": [
        "Anomaly detected and logged by Scanner Agent.",
        "Prior incidents and maintenance records reviewed by Investigator Agent."
      ],
      "open_actions": [
        "Inspect pressure valve actuator on PRESS-VALVE-23.",
        "Verify pressure sensor signal integrity.",
        "Confirm whether April 2026 follow-up calibration was completed."
      ]
    },
    "maintenance_request": {
      "priority": "HIGH",
      "asset": "PRESS-VALVE-23",
      "line_id": "LINE-B",
      "request": "Inspect, recalibrate, and test pressure valve actuator. Verify pressure sensor wiring and signal stability.",
      "reason": "Low pressure and output drop detected. Prior incident INC-2026-0312-LINE-B-004 was resolved by valve tuning."
    },
    "corrective_action_plan": {
      "problem": "Pressure instability and missing sensor data caused production output drop on Line B.",
      "containment": "Operate line at reduced speed or pause production until pressure is stable above 4.8 bar.",
      "root_cause_analysis": "Most likely: pressure valve actuator drift. Secondary: pressure sensor signal failure.",
      "corrective_action": "Tune valve actuator, verify sensor signal, and validate output recovery.",
      "preventive_action": "Add automated pressure-drift alert at 5.0 bar and update PM checklist."
    },
    "supplier_questions": []
  }
}
```

### Implementation — `backend/app/agents/technician_agent.py`

```python
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import settings
from services.pdf_service import generate_action_plan_pdf

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=1200,          # ← Memory guardrail
    openai_api_key=settings.openai_api_key,
)

TECHNICIAN_SYSTEM = """
You are the PLANT TECHNICIAN agent. Convert the investigation verdict into four operator documents.

Return STRICT JSON (no markdown):
{
  "shift_handoff_note": {
    "title": "...",
    "summary": "...",
    "current_status": "...",
    "actions_completed": ["..."],
    "open_actions": ["..."]
  },
  "maintenance_request": {
    "priority": "HIGH | MEDIUM | LOW",
    "asset": "...",
    "line_id": "...",
    "request": "...",
    "reason": "..."
  },
  "corrective_action_plan": {
    "problem": "...",
    "containment": "...",
    "root_cause_analysis": "...",
    "corrective_action": "...",
    "preventive_action": "..."
  },
  "supplier_questions": []
}

Guidelines:
- shift_handoff_note  : Clear for incoming shift. What happened, what's open, what to watch.
- maintenance_request : Formal CMMS-ready text with asset ID, line, priority, and reason.
- corrective_action_plan : Based on 8D/CAPA structure. Actionable and specific.
- supplier_questions  : Only if anomaly involves supplier parts or deliveries; else empty list.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", TECHNICIAN_SYSTEM),
    ("human",
     "INVESTIGATION VERDICT:\n{investigator_result}\n\n"
     "SCANNER ANOMALY:\n{scanner_result}\n\n"
     "Generate all four sections."),
])

async def technician_node(state: dict) -> dict:
    chain    = prompt | llm
    response = await chain.ainvoke({
        "investigator_result": json.dumps(state["investigator_result"], indent=2),
        "scanner_result":      json.dumps(state["scanner_result"],      indent=2),
    })

    content = response.content.strip()
    if content.startswith("```"):
        parts   = content.split("```")
        content = parts[1][4:] if parts[1].startswith("json") else parts[1]

    tech_output = json.loads(content.strip())

    pdf_path = generate_action_plan_pdf(
        run_id           = state["run_id"],
        scanner_result   = state["scanner_result"],
        investigator     = state["investigator_result"],
        technician       = tech_output,
    )
    tech_output["pdf_path"] = pdf_path

    return {
        **state,
        "technician_result": tech_output,
        "final_report_path": pdf_path,
        "approval_status":   "pending",   # human-in-the-loop gate opens here
    }
```

## 2.6 LangGraph Workflow — `backend/app/workflows/manufacturing_graph.py`

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agents.scanner_agent      import scanner_node
from agents.investigator_agent import investigator_node
from agents.technician_agent   import technician_node
from config import settings

def route_after_scanner(state: dict) -> str:
    return "investigator" if state.get("has_anomaly") else END

async def build_graph() -> StateGraph:
    # ── Memory Guardrail: PostgreSQL checkpointer ────────────────────────
    # Provides crash recovery, run replay, and inter-run isolation.
    # Each run_id becomes its own checkpoint thread — no state bleed.
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.database_url)
    await checkpointer.setup()

    g = StateGraph(dict)
    g.add_node("scanner",      scanner_node)
    g.add_node("investigator", investigator_node)
    g.add_node("technician",   technician_node)

    g.set_entry_point("scanner")
    g.add_conditional_edges("scanner", route_after_scanner,
                             {"investigator": "investigator", END: END})
    g.add_edge("investigator", "technician")
    g.add_edge("technician",   END)

    return g.compile(checkpointer=checkpointer)

_graph = None

async def get_graph():
    global _graph
    if _graph is None:
        _graph = await build_graph()
    return _graph

async def run_pipeline(run_id: str, state: dict) -> dict:
    graph  = await get_graph()
    # ── Memory Guardrail: thread-isolated concurrent runs ────────────────
    # RunnableConfig threads state by run_id — no bleed between parallel
    # incidents from different lines or plants.
    config = {"configurable": {"thread_id": run_id}}
    return await graph.ainvoke(state, config=config)
```

## 2.7 Memory Guardrails — Full Reference

All five guardrails work together to make the pipeline cost-predictable and crash-safe.

| Guardrail | Location | What It Prevents |
|---|---|---|
| `_trim_batch()` + tiktoken | `scanner_agent.py` | Unbounded sensor JSON flooding the Scanner prompt |
| `_build_kb_context()` budget | `investigator_agent.py` | Runaway Pinecone chunks exceeding context window |
| `max_tokens` per agent | All three agents | Runaway LLM generation (Scanner 800, Investigator 1500, Technician 1200) |
| PostgreSQL checkpointer | `manufacturing_graph.py` | Data loss on crash; enables run replay and audit |
| `thread_id = run_id` config | `manufacturing_graph.py` | State bleed between concurrent pipeline runs |
| UI buffer `slice(0, 200)` | `useSensorStream.ts` | Unbounded frontend list growth crashing the browser tab |
| Scoped Pinecone filter | `investigator_agent.py` | Retrieving irrelevant docs from other plants or lines |
| Human approval gate | `technician_agent.py` + frontend | AI directly creating CMMS tickets or contacting suppliers |

### Retry Wrapper — `backend/app/services/llm_utils.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

log = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def safe_llm_call(chain, inputs: dict) -> str:
    """Wraps any LangChain chain call with exponential-backoff retry."""
    response = await chain.ainvoke(inputs)
    return response.content
```

### Structured Logging — Thread `run_id` throughout

```python
import structlog
log = structlog.get_logger()

async def scanner_node(state: dict) -> dict:
    log.info("scanner.start",
             run_id=state["run_id"],
             line_id=state.get("line_id"),
             batch_size=len(state["raw_sensor_data"]))
    # ... logic ...
    log.info("scanner.done",
             run_id=state["run_id"],
             anomaly_detected=result.get("anomaly_detected"),
             severity=result.get("severity"))
    return {...}
```

---

# Module 3 — Technical Architecture & Implementation

## 3.1 Recommended Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Vite + React + TypeScript | SPA, SSE consumer, approval UI |
| UI Components | Shadcn/UI + Tailwind CSS | Accessible, consistent design system |
| Backend | FastAPI + Python | REST API, SSE stream, pipeline orchestration |
| Agent Orchestration | LangGraph + LangChain | Stateful multi-agent workflow |
| LLM | OpenAI GPT-4o | Reasoning, structured output generation |
| Vector DB | Pinecone | Semantic search over KB, SOPs, incidents |
| Relational DB | PostgreSQL | Issues, runs, approvals, audit log |
| PDF | ReportLab | Branded corrective action plan PDF |
| Deployment | Docker Compose | Local dev; Kubernetes path in Phase 3 |

## 3.2 Repository Structure

```
manufacturing-issue-resolution-assistant/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
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
│
├── data/
│   ├── simulated_sensor_data/
│   ├── plant_history/
│   │   └── seed.sql
│   ├── maintenance_records/
│   ├── prior_incidents/
│   ├── sop_documents/
│   └── pinecone_seed/
│       └── seed_pinecone.py
│
├── reports/
│   └── generated_pdfs/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

## 3.3 FastAPI Backend — `backend/app/main.py`

```python
import asyncio, json, uuid
from datetime import datetime, timezone
from typing  import AsyncGenerator

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel

from config import settings
from services.simulation_service import generate_stream, demo_scenario_line_b_pressure_drop
from workflows.manufacturing_graph import run_pipeline
from services.database_service import save_run, get_run, update_approval

app = FastAPI(title="Manufacturing Issue Resolution API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SSE: Sensor Stream ─────────────────────────────────────────────────────
@app.get("/stream/sensor")
async def sensor_stream(scenario: str = "live"):
    """Streams sensor batches as Server-Sent Events. Supports demo scenarios."""

    async def event_generator() -> AsyncGenerator[str, None]:
        loop = asyncio.get_event_loop()
        if scenario == "pressure_drop":
            batch = demo_scenario_line_b_pressure_drop()
            yield f"data: {json.dumps(batch)}\n\n"
            return                                    # one-shot demo
        gen = generate_stream(interval_seconds=1.5, anomaly_probability=0.12)
        while True:
            batch = await loop.run_in_executor(None, lambda: next(gen))
            yield f"data: {json.dumps(batch)}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ── Trigger Pipeline ───────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    problem_statement: str
    plant_id:          str
    line_id:           str
    timeframe_start:   str
    timeframe_end:     str
    sensor_batch:      list[dict]
    notes:             str = ""

@app.post("/api/issues/analyze")
async def analyze_issue(req: AnalyzeRequest, bg: BackgroundTasks):
    issue_id = f"ISSUE-{datetime.now().strftime('%Y-%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    bg.add_task(_run_pipeline_task, issue_id, req)
    return {"issue_id": issue_id, "status": "RUNNING"}

async def _run_pipeline_task(issue_id: str, req: AnalyzeRequest):
    initial = {
        "run_id":            issue_id,
        "problem_statement": req.problem_statement,
        "plant_id":          req.plant_id,
        "line_id":           req.line_id,
        "timeframe_start":   req.timeframe_start,
        "timeframe_end":     req.timeframe_end,
        "raw_sensor_data":   req.sensor_batch,
        "scanner_result":    None,
        "investigator_result": None,
        "technician_result": None,
        "approval_status":   "pending",
        "final_report_path": None,
        "has_anomaly":       False,
    }
    result = await run_pipeline(run_id=issue_id, state=initial)
    await save_run(issue_id, result)

# ── Poll Status ────────────────────────────────────────────────────────────
@app.get("/api/issues/{issue_id}")
async def get_issue(issue_id: str):
    run = await get_run(issue_id)
    if not run:
        raise HTTPException(status_code=404, detail="Issue not found")
    return run

# ── Human-in-the-Loop Approval Gate ───────────────────────────────────────
class ApprovalRequest(BaseModel):
    decision: str    # "approved" | "rejected"
    approver: str
    notes:    str = ""

@app.post("/api/issues/{issue_id}/approve")
async def approve_issue(issue_id: str, req: ApprovalRequest):
    """
    Required before the system creates CMMS maintenance tickets,
    sends supplier communications, or escalates safety incidents.
    """
    await update_approval(issue_id, req.decision, req.approver, req.notes)
    return {"issue_id": issue_id, "approval_status": req.decision}

# ── PDF Download ───────────────────────────────────────────────────────────
@app.get("/api/reports/{issue_id}/pdf")
async def download_pdf(issue_id: str):
    run = await get_run(issue_id)
    if run and run.get("final_report_path"):
        return FileResponse(
            run["final_report_path"],
            media_type="application/pdf",
            filename=f"action_plan_{issue_id}.pdf",
        )
    raise HTTPException(status_code=404, detail="PDF not ready")

# ── Simulation Trigger ─────────────────────────────────────────────────────
@app.post("/api/simulation/start")
async def start_simulation():
    return {"status": "started", "message": "Use GET /stream/sensor to connect SSE"}
```

## 3.4 Database Schema — PostgreSQL

```sql
-- ── Core Tables ────────────────────────────────────────────────────────────
CREATE TABLE plants (
    id       TEXT PRIMARY KEY,
    name     TEXT,
    location TEXT,
    timezone TEXT
);

CREATE TABLE production_lines (
    id           TEXT PRIMARY KEY,
    plant_id     TEXT REFERENCES plants(id),
    name         TEXT,
    product_type TEXT
);

CREATE TABLE quality_thresholds (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id        TEXT REFERENCES production_lines(id),
    metric         TEXT,
    warning_low    DOUBLE PRECISION,
    warning_high   DOUBLE PRECISION,
    critical_low   DOUBLE PRECISION,
    critical_high  DOUBLE PRECISION,
    unit           TEXT
);

CREATE TABLE maintenance_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_id         TEXT REFERENCES production_lines(id),
    machine_id      TEXT,
    event_date      DATE,
    event_type      TEXT,
    description     TEXT,
    resolved_by     TEXT,
    resolution_note TEXT
);

-- ── Pipeline Tables ────────────────────────────────────────────────────────
CREATE TABLE production_issues (
    issue_id          TEXT PRIMARY KEY,
    plant_id          TEXT,
    line_id           TEXT,
    problem_statement TEXT,
    timeframe_start   TIMESTAMP,
    timeframe_end     TIMESTAMP,
    severity          TEXT,
    status            TEXT DEFAULT 'RUNNING',  -- RUNNING | DONE | ERROR
    approval_status   TEXT DEFAULT 'pending',  -- pending | approved | rejected
    approver          TEXT,
    approval_notes    TEXT,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE anomaly_events (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id        TEXT REFERENCES production_issues(issue_id),
    machine_id      TEXT,
    anomaly_type    TEXT,
    metric_name     TEXT,
    metric_value    DOUBLE PRECISION,
    threshold_value DOUBLE PRECISION,
    timestamp       TIMESTAMP,
    severity        TEXT
);

CREATE TABLE pipeline_runs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id             TEXT REFERENCES production_issues(issue_id),
    scanner_output       JSONB,
    investigator_output  JSONB,
    technician_output    JSONB,
    retrieved_context    TEXT,
    pdf_path             TEXT,
    created_at           TIMESTAMP DEFAULT NOW()
);

CREATE TABLE maintenance_requests (
    request_id   TEXT PRIMARY KEY,
    issue_id     TEXT REFERENCES production_issues(issue_id),
    asset_id     TEXT,
    priority     TEXT,
    request_text TEXT,
    status       TEXT DEFAULT 'PENDING',   -- PENDING | APPROVED | SUBMITTED | CLOSED
    created_at   TIMESTAMP DEFAULT NOW()
);

-- ── Audit Log (immutable) ─────────────────────────────────────────────────
CREATE TABLE audit_log (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id   TEXT,
    event_type TEXT,   -- scanner_complete | investigator_complete | approval | pdf_generated
    actor      TEXT,   -- "system" or username
    payload    JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 3.5 PDF Generator — `backend/app/services/pdf_service.py`

```python
import os
from datetime import datetime
from reportlab.lib.pagesizes   import A4
from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units       import mm
from reportlab.lib             import colors
from reportlab.platypus        import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

REPORT_DIR = os.environ.get("REPORT_DIR", "/tmp/reports")
os.makedirs(REPORT_DIR, exist_ok=True)

C_NAVY      = colors.HexColor("#1E3A5F")
C_STABILIZE = colors.HexColor("#E63946")
C_INVEST    = colors.HexColor("#F4A261")
C_PREVENT   = colors.HexColor("#2A9D8F")

VERDICT_COLOR = {
    "Stabilize":          C_STABILIZE,
    "Investigate":        C_INVEST,
    "Prevent Recurrence": C_PREVENT,
}

def generate_action_plan_pdf(run_id, scanner_result, investigator, technician) -> str:
    path   = os.path.join(REPORT_DIR, f"action_plan_{run_id[:12]}.pdf")
    doc    = SimpleDocTemplate(path, pagesize=A4,
                                topMargin=15*mm, bottomMargin=15*mm,
                                leftMargin=20*mm, rightMargin=20*mm)
    styles = getSampleStyleSheet()
    story  = []

    h1   = ParagraphStyle("H1", parent=styles["Heading1"], textColor=C_NAVY, fontSize=18, spaceAfter=6)
    h2   = ParagraphStyle("H2", parent=styles["Heading2"], textColor=C_NAVY, fontSize=12, spaceAfter=4)
    body = styles["BodyText"]
    sm   = ParagraphStyle("SM", parent=body, fontSize=9, textColor=colors.grey)

    def section(title: str):
        story.append(Spacer(1, 6*mm))
        story.append(HRFlowable(width="100%", color=C_NAVY, thickness=0.8))
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(title, h2))

    # Header
    story.append(Paragraph("Manufacturing Issue Resolution Report", h1))
    story.append(Paragraph(
        f"Issue ID: {run_id}  ·  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        sm,
    ))
    story.append(Spacer(1, 4*mm))

    # Verdict banner
    verdict  = investigator.get("verdict", "Unknown")
    v_color  = VERDICT_COLOR.get(verdict, C_NAVY)
    v_table  = Table(
        [[Paragraph(f"VERDICT: {verdict.upper()}",
            ParagraphStyle("V", fontSize=14, textColor=colors.white, fontName="Helvetica-Bold"))]],
        colWidths=["100%"],
    )
    v_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), v_color),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(v_table)
    story.append(Spacer(1, 4*mm))

    # Anomaly Summary
    section("1. Detected Anomalies")
    for detail in scanner_result.get("details", []):
        story.append(Paragraph(f"• {detail}", body))

    # Root Cause Hypotheses
    section("2. Root Cause Hypotheses")
    for i, h in enumerate(investigator.get("root_cause_hypotheses", []), 1):
        pct = int(h["confidence"] * 100)
        story.append(Paragraph(f"<b>Hypothesis {i}</b> — Confidence: {pct}%", h2))
        story.append(Paragraph(h["hypothesis"], body))
        for ev in h.get("supporting_evidence", []):
            story.append(Paragraph(f"  ✓ {ev}", body))
        story.append(Spacer(1, 3*mm))

    # Recommendations
    section("3. Recommendations")
    tiers = [("stabilize", "🔴 STABILIZE", C_STABILIZE),
             ("investigate", "🟠 INVESTIGATE", C_INVEST),
             ("prevent_recurrence", "🟢 PREVENT RECURRENCE", C_PREVENT)]
    recs  = investigator.get("recommendations", {})
    for key, label, color in tiers:
        items = recs.get(key, [])
        if items:
            story.append(Paragraph(label, ParagraphStyle(
                f"t_{key}", parent=body, fontName="Helvetica-Bold",
                textColor=color, fontSize=10)))
            for item in items:
                story.append(Paragraph(f"  • {item}", body))
            story.append(Spacer(1, 2*mm))

    # Shift Handoff Note
    section("4. Shift Handoff Note")
    note = technician.get("shift_handoff_note", {})
    story.append(Paragraph(f"<b>{note.get('title','')}</b>", body))
    story.append(Paragraph(note.get("summary", ""), body))
    story.append(Paragraph(f"<b>Current status:</b> {note.get('current_status','')}", body))
    for action in note.get("open_actions", []):
        story.append(Paragraph(f"  □ {action}", body))

    # Maintenance Request
    section("5. Maintenance Request (CMMS)")
    req = technician.get("maintenance_request", {})
    story.append(Paragraph(
        f"<b>Priority:</b> {req.get('priority','')}  ·  "
        f"<b>Asset:</b> {req.get('asset','')}  ·  "
        f"<b>Line:</b> {req.get('line_id','')}", body))
    story.append(Paragraph(req.get("request", ""), body))

    # CAPA
    section("6. Corrective Action Plan")
    capa = technician.get("corrective_action_plan", {})
    for field, label in [("problem","Problem"), ("containment","Containment"),
                         ("root_cause_analysis","Root Cause"),
                         ("corrective_action","Corrective Action"),
                         ("preventive_action","Preventive Action")]:
        story.append(Paragraph(f"<b>{label}:</b> {capa.get(field,'')}", body))
        story.append(Spacer(1, 1*mm))

    # Compliance
    section("7. Compliance References")
    for ref in investigator.get("compliance_reference", []):
        story.append(Paragraph(f"  ✔ {ref}", body))

    # Footer
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", color=colors.lightgrey, thickness=0.5))
    story.append(Paragraph(
        "Generated by Manufacturing Issue Resolution System · Confidential",
        ParagraphStyle("Footer", parent=sm, alignment=1),
    ))

    doc.build(story)
    return path
```

## 3.6 Docker Compose

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER:     mfg_user
      POSTGRES_PASSWORD: password
      POSTGRES_DB:       manufacturing
    ports:   ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]

  backend:
    build: ./backend
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://mfg_user:password@postgres:5432/manufacturing
    ports:      ["8000:8000"]
    depends_on: [postgres]
    volumes:    [./reports:/tmp/reports]
    command:    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:      ["5173:5173"]
    depends_on: [backend]
    command:    npm run dev -- --host

volumes:
  pgdata:
```

## 3.7 Environment Variables

```dotenv
# .env.example
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=
DATABASE_URL=
REPORT_DIR=/tmp/reports

# LangSmith observability (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=mfg-issue-resolution
```

---

# Module 4 — Roadmap, Best Practices & Deliverables

## 4.1 Implementation Roadmap

### Phase 1 — MVP (Weeks 1–4)

**Scope:** Simulated data · Rule-based scanner · Three-agent pipeline · Pinecone RAG · PDF report · Frontend dashboard

**MVP Features:**
- Start Production Stream button with scenario selector
- Plant and line selector
- Problem statement input field
- Scanner Agent anomaly alert card
- Agent pipeline stepper (Scanner → Investigator → Technician)
- Investigator verdict with root-cause hypotheses and weighted confidence bars
- Technician action package with shift handoff note, maintenance request, CAPA
- Downloadable PDF report
- Human approval gate before CMMS action

### Phase 2 — Better Context & Retrieval (Weeks 5–8)

**Add More Knowledge Sources:**
- SOP document library (full PDFs chunked and embedded)
- Expanded maintenance logs (12-month history)
- Quality inspection reports
- Supplier delivery records
- Downtime records and shift notes
- Safety alerts and near-miss reports

**Improve RAG Quality:**
- Metadata filtering by plant, line, machine, issue type, and date range
- Hybrid search: keyword + vector retrieval
- Cross-encoder reranking to improve evidence quality
- Citation reference tracking (which doc, which chunk)

**Example Pinecone Metadata Schema:**

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

### Phase 3 — Production-Grade Integrations (Weeks 9–14)

**Real Integrations:**
- PLC / SCADA data connector
- MES integration for production order context
- CMMS integration for direct maintenance ticket creation (post-approval)
- ERP or supplier portal integration
- Email / Microsoft Teams notification
- Grafana dashboard for sensor trends

**Infrastructure Upgrades:**
- Celery + Redis for async pipeline queuing
- Kafka or MQTT for real-time IoT streaming
- InfluxDB or TimescaleDB for time-series sensor storage
- Kubernetes deployment with separate pods per agent

**Governance:**
- Role-based access control (RBAC)
- Versioned prompt templates with A/B testing
- Full audit trail of AI recommendations and human approvals
- Confidence threshold gates before auto-escalation

### Phase 4 — Advanced AI & Operational Intelligence (Weeks 15+)

**Advanced Features:**
- Time-series anomaly detection model (Isolation Forest or LSTM)
- Predictive maintenance scoring
- Supplier delay prediction from lead-time trends
- Quality defect pattern detection across shifts
- Automatic CAPA generation from historical patterns
- Voice or mobile shift handoff assistant
- Operator feedback loop to improve future recommendations

---

## 4.2 Best Practices

### 1. Keep AI Recommendations Explainable

Every recommendation must reference evidence from:
- Current sensor data
- Prior incidents (with incident IDs)
- Maintenance history (with record IDs)
- SOPs or process standards (with document IDs and revision)
- Quality thresholds (with metric and threshold values)

### 2. Use Weighted Confidence Carefully

Confidence scores are not arbitrary — they are computed from four observable signals:

```json
{
  "confidence_scoring": {
    "historical_similarity":        0.35,
    "threshold_violation_strength": 0.25,
    "maintenance_history_match":    0.25,
    "data_completeness":            0.15
  }
}
```

Surface the breakdown in the UI so plant managers understand *why* a confidence score is high or low.

### 3. Separate Stabilization from Root-Cause Investigation

In manufacturing, these are different time horizons and different owners:
- **Stabilize** → Shift operator acts NOW to protect people and equipment
- **Investigate** → Maintenance or process engineer acts within this shift or the next
- **Prevent Recurrence** → Engineering or management acts within days or weeks

### 4. Never Let the LLM Directly Control Physical Systems

The assistant recommends actions. It must **never** directly:
- Write to PLC registers or SCADA setpoints
- Open or close valves, relays, or safety systems
- Send automated commands to robots or conveyors
- Override machine interlocks

All physical actions must go through a human operator.

### 5. Require Human-in-the-Loop Approval Before:

- Creating a CMMS maintenance ticket
- Sending supplier communication or purchase orders
- Updating SOPs or quality thresholds
- Closing corrective actions
- Escalating safety incidents to regulatory bodies

The approval gate in the API (`POST /api/issues/{issue_id}/approve`) enforces this programmatically.

### 6. Log Everything — Immutably

The `audit_log` table captures every significant event and must never be updated or deleted:
- User inputs and problem statements
- Raw sensor batch snapshot at time of trigger
- All three agent outputs (verbatim JSON)
- Retrieved evidence citations
- Final recommendations
- Human approvals and rejections
- Generated PDF paths and timestamps

### 7. Use Strict Structured Outputs

All agents return verified JSON schemas. Benefits:
- Predictable frontend rendering
- Easy unit testing (`assert result["verdict"] in VALID_VERDICTS`)
- Integration-ready for CMMS and MES systems
- Avoids hallucinated prose that operators might misinterpret

### 8. Apply All Memory Guardrails in Production

| Guardrail | Setting | Why |
|---|---|---|
| Scanner batch cap | 2,000 tokens | 4 lines × 60-second backlog = ~6,000 tokens without this |
| KB context budget | 3,000 tokens | 3 anomalies × 4 chunks = 12 chunks without a ceiling |
| Scanner max_tokens | 800 | Structured JSON — no need for long generation |
| Investigator max_tokens | 1,500 | Hypotheses + recommendations + compliance refs |
| Technician max_tokens | 1,200 | Four documents, all concise |
| Checkpointer | PostgreSQL | Crash recovery + audit trail |
| Thread isolation | `thread_id = run_id` | Concurrent incidents from multiple lines |

---

## 4.3 Demo Scenarios

| Scenario | Line | Trigger | Expected Verdict |
|---|---|---|---|
| Low pressure + output drop | LINE-B | `demo_scenario_line_b_pressure_drop()` | Stabilize |
| Temperature spike to 300°C | LINE-A | `TEMPERATURE_SPIKE` injection | Stabilize |
| Missing sensor data (DATA_GAP) | LINE-C | `DATA_GAP` injection | Investigate |
| High vibration trending up | LINE-C | `HIGH_VIBRATION` injection | Investigate |
| Repeated pressure pattern | LINE-B | Live stream with history in Pinecone | Prevent Recurrence |

### Recommended Demo Story (Plant Manager Walkthrough)

1. Plant manager opens dashboard and selects `PLANT-01` / `LINE-B`.
2. Selects **Demo: LINE-B Pressure Drop** and clicks **Start Production Stream**.
3. Scanner Agent detects: `LOW_PRESSURE`, `OUTPUT_DROP`, `MISSING_SENSOR_DATA` — severity `HIGH`.
4. Agent pipeline stepper advances: Scanner ✅ → Investigator 🔄 → Technician ⏳.
5. Investigator retrieves incident `INC-2026-0312-LINE-B-004` and maintenance record `MNT-2026-0428-009`.
6. Investigator issues verdict: **Stabilize** with 82% confidence on pressure valve actuator drift.
7. Confidence breakdown bar visualizes the four weighted components.
8. Technician generates shift handoff note, `HIGH` priority maintenance request for `PRESS-VALVE-23`, and CAPA.
9. Plant manager clicks **Approve** — approval logged to audit trail.
10. Plant manager downloads PDF corrective action plan.

---

## 4.4 Final Deliverables Checklist

### Engineering Deliverables

- [ ] Vite + React + Shadcn/UI frontend with SSE consumer
- [ ] FastAPI backend with all API endpoints
- [ ] Sensor simulation service with 4 anomaly profiles
- [ ] 4 named demo scenarios
- [ ] LangGraph multi-agent orchestration with checkpointer
- [ ] Scanner, Investigator, and Technician agents with full guardrails
- [ ] Pinecone ingestion pipeline with 7 seeded documents
- [ ] PostgreSQL schema with audit log
- [ ] PDF generation with ReportLab
- [ ] Docker Compose for full local stack

### AI Deliverables

- [ ] Scanner Agent system prompt + rule JSON + output schema
- [ ] Investigator Agent system prompt + weighted confidence schema
- [ ] Plant Technician Agent system prompt + CAPA schema
- [ ] Pinecone seed script with metadata filters
- [ ] Sample JSON: 2 prior incidents, 2 maintenance records, 3 SOP chunks
- [ ] Evaluation examples for all 5 demo scenarios

### Business Deliverables

- [ ] Demo scenario: LINE-B low pressure + output drop
- [ ] Demo scenario: temperature spike to 300°C
- [ ] Demo scenario: missing production data (DATA_GAP)
- [ ] PDF corrective action plan template
- [ ] Shift handoff template
- [ ] Maintenance request template (CMMS-compatible)
- [ ] Approval workflow documentation for plant managers

---

*Manufacturing Issue Resolution Assistant — Multi-Agent Implementation Guide*
*Final Version · Merged from implementation plan + domain best practices + memory guardrails*
