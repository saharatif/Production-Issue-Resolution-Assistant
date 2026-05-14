# Production Issue Resolution Assistant Roadmap

## Phase 1 - MVP
- Simulated IoT data stream with named demo scenarios.
- Rule-based Scanner, Investigator, and Plant Technician workflow.
- Human approval gate before external action.
- PDF corrective action plan generation.
- Frontend dashboard with SSE stream, pipeline status, recommendations, approval, and PDF download.

## Phase 2 - Better Context and Retrieval
- Add full SOP PDFs, 12-month maintenance logs, quality inspection reports, supplier records, downtime logs, and shift notes.
- Add metadata filtering by plant, line, machine, issue type, and date range.
- Add hybrid keyword/vector retrieval and source-level citation tracking.

## Phase 3 - Production Integrations
- Add PLC/SCADA read-only ingestion through OPC-UA or MQTT.
- Add MES/CMMS integrations, gated by human approval.
- Move background execution to Celery/Redis or a queue-backed worker.
- Add RBAC and immutable audit review screens.

## Phase 4 - Advanced Operations Intelligence
- Add time-series anomaly models.
- Add predictive maintenance scoring.
- Add supplier delay prediction.
- Add operator feedback loops for recommendation quality.
