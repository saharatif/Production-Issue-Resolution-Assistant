# Approval Workflow

The assistant recommends operational actions only. It must never directly control plant equipment or create external tickets before a qualified human approves.

## Flow
1. Scanner detects or clears anomalies.
2. Investigator produces evidence-backed hypotheses and recommendations.
3. Technician creates shift handoff, maintenance request, corrective action plan, and PDF.
4. The run remains `approval_status: pending`.
5. A plant manager approves or rejects with `POST /api/issues/{issue_id}/approve`.
6. Approval decisions are written to the audit log.

## Human Gate Applies Before
- Creating CMMS tickets.
- Sending supplier communications.
- Updating SOPs or quality thresholds.
- Closing corrective actions.
- Escalating safety incidents.
