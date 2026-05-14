# Module 2 Plan — Multi-Agent Architecture

## Goal
Implement the three-agent LangGraph pipeline: Scanner → Investigator → Plant Technician. Each agent has a defined role, structured JSON input/output contract, token guardrails, and a single LangGraph node function. The pipeline routes automatically based on anomaly detection and pauses at a human-approval gate before taking external actions.

---

## Deliverables

| # | Deliverable | Path |
|---|---|---|
| 1 | LangGraph state definition | `backend/app/workflows/manufacturing_graph.py` |
| 2 | Scanner Agent | `backend/app/agents/scanner_agent.py` |
| 3 | Scanner rules config | `data/scanner_rules.json` |
| 4 | Investigator Agent | `backend/app/agents/investigator_agent.py` |
| 5 | Technician Agent | `backend/app/agents/technician_agent.py` |
| 6 | Retry wrapper | `backend/app/services/llm_utils.py` |
| 7 | Structured logging setup | (inline in each agent) |
| 8 | Human approval gate | (via `approval_status` field + FastAPI endpoint) |

---

## Step-by-Step Plan

### Step 1 — Define LangGraph State
File: `backend/app/workflows/manufacturing_graph.py`

```python
class ManufacturingIssueState(TypedDict):
    run_id, problem_statement, plant_id, line_id
    timeframe_start, timeframe_end
    raw_sensor_data: List[Dict]
    scanner_result, retrieved_context, investigator_result, technician_result
    approval_status: str   # "pending" | "approved" | "rejected"
    final_report_path: Optional[str]
    has_anomaly: bool
```

All three agents read from and write to this shared state dict.

### Step 2 — Build Scanner Agent
File: `backend/app/agents/scanner_agent.py`

**Logic flow:**
1. Apply `_trim_batch()` → cap incoming sensor JSON to **2,000 tokens** (tiktoken)
2. Send trimmed batch to GPT-4o with `temperature=0`, `max_tokens=800`
3. System prompt defines all 5 anomaly types and severity levels
4. Parse strict JSON response (strip markdown fences if present)
5. Set `has_anomaly` and `scanner_result` in state

**Rules JSON** (`data/scanner_rules.json`): 6 rules covering temperature, pressure, vibration, output, and null checks.

**Output schema:**
```json
{
  "anomaly_detected": true,
  "plant_id": "...", "line_id": "...", "machine_id": "...",
  "anomaly_type": ["LOW_PRESSURE", "OUTPUT_DROP"],
  "severity": "HIGH",
  "details": ["..."],
  "recommended_next_agent": "Investigator Agent"
}
```

### Step 3 — Build Investigator Agent
File: `backend/app/agents/investigator_agent.py`

**Logic flow:**
1. Build KB context via `_build_kb_context()` — query Pinecone, deduplicate, cap at **3,000 tokens**
2. Use scoped metadata filter: `{"line_id": {"$eq": line_id}}` to avoid cross-plant noise
3. Send anomalies + KB context to GPT-4o with `temperature=0.1`, `max_tokens=1500`
4. Parse strict JSON response

**Confidence breakdown weights** (must sum to 1.0):
- `historical_similarity`: 0.35
- `threshold_violation_strength`: 0.25
- `maintenance_history_match`: 0.25
- `data_completeness`: 0.15

**Verdict options:** `"Stabilize"` | `"Investigate"` | `"Prevent Recurrence"`

**Output schema:**
```json
{
  "verdict": "Stabilize",
  "root_cause_hypotheses": [
    {
      "hypothesis": "...",
      "confidence": 0.82,
      "confidence_breakdown": { ... },
      "supporting_evidence": ["..."]
    }
  ],
  "recommendations": {
    "stabilize": [...], "investigate": [...], "prevent_recurrence": [...]
  },
  "compliance_reference": ["..."]
}
```

### Step 4 — Build Technician Agent
File: `backend/app/agents/technician_agent.py`

**Logic flow:**
1. Receive `investigator_result` + `scanner_result` from state
2. Send to GPT-4o with `temperature=0.2`, `max_tokens=1200`
3. Parse strict JSON response with 4 sections
4. Call `generate_action_plan_pdf()` → write PDF, return path
5. Set `approval_status = "pending"` (human gate opens here)

**Output schema (4 sections):**
- `shift_handoff_note` — title, summary, current_status, actions_completed, open_actions
- `maintenance_request` — priority, asset, line_id, request, reason
- `corrective_action_plan` — problem, containment, root_cause_analysis, corrective_action, preventive_action
- `supplier_questions` — list (empty unless supplier-related)

### Step 5 — Wire LangGraph Graph
File: `backend/app/workflows/manufacturing_graph.py`

```
START
  └─► scanner_node
        ├─► (has_anomaly=False) ──► END
        └─► (has_anomaly=True)  ──► investigator_node
                                          └─► technician_node ──► END
```

- Use `AsyncPostgresSaver` checkpointer (crash recovery + audit)
- Use `thread_id = run_id` in `RunnableConfig` (inter-run isolation)
- Singleton `_graph` cached after first `build_graph()` call

### Step 6 — Retry Wrapper
File: `backend/app/services/llm_utils.py`

- `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))`
- Wraps any `chain.ainvoke()` call
- Re-raises after 3 failed attempts (caller handles)

### Step 7 — Structured Logging
- Use `structlog` in every agent node
- Bind `run_id` and `line_id` at start of each node
- Log: `{agent}.start` and `{agent}.done` with key output fields

---

## Memory Guardrails (this module)

| Guardrail | Where | Value |
|---|---|---|
| Batch token cap | `scanner_agent._trim_batch()` | 2,000 tokens |
| KB context budget | `investigator_agent._build_kb_context()` | 3,000 tokens |
| Scanner `max_tokens` | `ChatOpenAI(max_tokens=800)` | 800 |
| Investigator `max_tokens` | `ChatOpenAI(max_tokens=1500)` | 1,500 |
| Technician `max_tokens` | `ChatOpenAI(max_tokens=1200)` | 1,200 |
| Checkpointer | `AsyncPostgresSaver` | PostgreSQL |
| Thread isolation | `thread_id = run_id` | Per run |
| Scoped Pinecone filter | `{"line_id": {"$eq": line_id}}` | Per line |
| Human gate | `approval_status = "pending"` | Before CMMS action |

---

## Agent Routing Logic

```python
def route_after_scanner(state: dict) -> str:
    return "investigator" if state.get("has_anomaly") else END
```

If the scanner returns `anomaly_detected: false`, the pipeline terminates immediately — no LLM calls for Investigator or Technician. This keeps clean-batch runs zero-cost for those agents.

---

## Acceptance Criteria

- [ ] Scanner correctly classifies all 5 anomaly types and returns valid JSON
- [ ] Scanner returns `anomaly_detected: false` for normal readings with no LLM hallucination
- [ ] Investigator retrieves ≥1 relevant KB document for LINE-B pressure scenarios
- [ ] Investigator confidence breakdown components sum to ≤ 1.0
- [ ] Technician produces all 4 document sections in a single LLM call
- [ ] PDF is written to disk and path stored in state
- [ ] `approval_status` is always `"pending"` after Technician completes
- [ ] LangGraph checkpointer persists state to PostgreSQL after each node
- [ ] Two concurrent runs with different `run_id`s do not share state
- [ ] Retry wrapper retries up to 3× on OpenAI API errors

---

## Dependencies

- `langgraph`, `langchain`, `langchain-openai`
- `openai` (GPT-4o)
- `pinecone` (via `pinecone_service.py`)
- `tiktoken` (batch and context token counting)
- `tenacity` (retry wrapper)
- `structlog` (structured logging)
- `asyncpg` + `langgraph[postgres]` (checkpointer)
- `reportlab` (PDF, called from Technician)

---

## Environment Variables Required (this module)
```
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=manufacturing-kb
DATABASE_URL=
```
