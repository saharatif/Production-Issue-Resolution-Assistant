"""Technician agent: creates operator-ready action documents and report PDF."""

from __future__ import annotations

import json
from typing import Any

from app.services.pdf_service import generate_action_plan_pdf


def _log(event: str, **fields: Any) -> None:
    try:
        import structlog

        structlog.get_logger().info(event, **fields)
    except Exception:
        print(json.dumps({"event": event, **fields}, sort_keys=True))


def _priority(scanner_result: dict[str, Any]) -> str:
    return "HIGH" if scanner_result.get("severity") in ("HIGH", "CRITICAL") else "MEDIUM"


async def technician_node(state: dict[str, Any]) -> dict[str, Any]:
    scanner = state["scanner_result"]
    investigator = state["investigator_result"]
    _log("technician.start", run_id=state["run_id"], line_id=state.get("line_id"))

    line_id = scanner.get("line_id") or state.get("line_id")
    asset = scanner.get("machine_id") or "UNKNOWN-ASSET"
    hypothesis = investigator["root_cause_hypotheses"][0]["hypothesis"]
    result = {
        "shift_handoff_note": {
            "title": f"Shift Handoff: {line_id} Production Anomaly",
            "summary": f"{line_id} reported {', '.join(scanner.get('anomaly_type', []))}.",
            "current_status": "Keep line in controlled operation until maintenance checks are complete.",
            "actions_completed": [
                "Scanner Agent detected and classified the anomaly.",
                "Investigator Agent reviewed relevant operational context.",
            ],
            "open_actions": [
                f"Inspect {asset}.",
                "Verify sensor signal integrity and recent maintenance records.",
            ],
        },
        "maintenance_request": {
            "priority": _priority(scanner),
            "asset": asset,
            "line_id": line_id,
            "request": "Inspect, test, and restore the affected equipment to normal operating range.",
            "reason": hypothesis,
        },
        "corrective_action_plan": {
            "problem": "; ".join(scanner.get("details", [])) or "Production anomaly detected.",
            "containment": "Reduce speed or pause operation until readings return to stable range.",
            "root_cause_analysis": hypothesis,
            "corrective_action": "Repair or recalibrate affected equipment, then validate recovery with live readings.",
            "preventive_action": "Add early-warning alert and update preventive maintenance checklist.",
        },
        "supplier_questions": [],
    }

    pdf_path = generate_action_plan_pdf(
        run_id=state["run_id"],
        scanner_result=scanner,
        investigator=investigator,
        technician=result,
    )
    result["pdf_path"] = pdf_path

    _log("technician.done", run_id=state["run_id"], pdf_path=pdf_path, approval_status="pending")
    return {
        **state,
        "technician_result": result,
        "final_report_path": pdf_path,
        "approval_status": "pending",
    }
