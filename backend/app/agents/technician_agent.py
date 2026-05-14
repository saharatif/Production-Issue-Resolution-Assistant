"""Technician agent: creates operator-ready action documents and report PDF."""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.services.llm_utils import parse_json_response, safe_llm_call
from app.services.pdf_service import generate_action_plan_pdf


SYSTEM_PROMPT = """You are a manufacturing plant technician agent. Given the scanner anomaly \
report and the investigator's root-cause findings, produce operator-ready action documents \
as strict JSON.

Respond with ONLY valid JSON — no markdown fences, no prose outside the JSON object.

Required schema:
{
  "shift_handoff_note": {
    "title": "<line ID> Shift Handoff — <brief anomaly label>",
    "summary": "<2-3 sentences describing what happened, which machines, which metrics>",
    "current_status": "<one sentence on the current operating state>",
    "actions_completed": ["<specific action already taken>"],
    "open_actions": ["<specific action the next shift must complete>"]
  },
  "maintenance_request": {
    "priority": "HIGH" | "MEDIUM" | "LOW",
    "asset": "<machine ID>",
    "line_id": "<line ID>",
    "request": "<specific maintenance task referencing the anomaly>",
    "reason": "<root cause hypothesis linked to the sensor readings>"
  },
  "corrective_action_plan": {
    "problem": "<precise description of the production problem with metric values>",
    "containment": "<immediate action to stabilise production now>",
    "root_cause_analysis": "<root cause from investigator output>",
    "corrective_action": "<specific repair or recalibration step>",
    "preventive_action": "<long-term PM or alert update to prevent recurrence>"
  },
  "supplier_questions": ["<question to raise with a supplier if relevant, else empty list>"]
}

Rules:
- Reference specific machine IDs, line IDs, metric values, and thresholds from the input
- actions_completed and open_actions must each have at least 2 specific entries
- corrective_action_plan.problem must include at least one actual sensor reading value
- All text must be specific to THIS incident — no generic filler phrases
"""


def _log(event: str, **fields: Any) -> None:
    try:
        import structlog
        structlog.get_logger().info(event, **fields)
    except Exception:
        print(json.dumps({"event": event, **fields}, sort_keys=True))


def _priority(scanner_result: dict[str, Any]) -> str:
    return "HIGH" if scanner_result.get("severity") in ("HIGH", "CRITICAL") else "MEDIUM"


def _fallback_result(state: dict[str, Any]) -> dict[str, Any]:
    scanner = state["scanner_result"]
    investigator = state["investigator_result"]
    line_id = scanner.get("line_id") or state.get("line_id", "UNKNOWN")
    asset = scanner.get("machine_id") or "UNKNOWN-ASSET"
    hypothesis = investigator["root_cause_hypotheses"][0]["hypothesis"]
    anomalies = ", ".join(scanner.get("anomaly_type", []))
    details = "; ".join(scanner.get("details", []))
    return {
        "shift_handoff_note": {
            "title": f"Shift Handoff: {line_id} — {anomalies}",
            "summary": (
                f"{line_id} reported {anomalies} on {asset}. "
                f"Detected: {details}. "
                "Investigator has completed root-cause analysis."
            ),
            "current_status": "Line in controlled operation pending maintenance inspection.",
            "actions_completed": [
                f"Scanner detected and classified anomaly: {anomalies} (severity {scanner.get('severity')}).",
                "Investigator completed root-cause analysis and generated recommendations.",
            ],
            "open_actions": [
                f"Maintenance team to inspect {asset} on {line_id}.",
                "Verify sensor signal integrity and confirm readings after corrective action.",
            ],
        },
        "maintenance_request": {
            "priority": _priority(scanner),
            "asset": asset,
            "line_id": line_id,
            "request": f"Inspect, test, and restore {asset} to normal operating range following {anomalies} event.",
            "reason": hypothesis,
        },
        "corrective_action_plan": {
            "problem": details or f"Production anomaly detected: {anomalies}.",
            "containment": "Reduce line speed or pause operation until readings return to stable range.",
            "root_cause_analysis": hypothesis,
            "corrective_action": "Repair or recalibrate affected equipment, then validate with live readings.",
            "preventive_action": "Add early-warning alert and update preventive maintenance checklist.",
        },
        "supplier_questions": [],
    }


async def technician_node(state: dict[str, Any]) -> dict[str, Any]:
    scanner = state["scanner_result"]
    investigator = state["investigator_result"]
    _log("technician.start", run_id=state["run_id"], line_id=state.get("line_id"))

    result = None

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            user_msg = (
                f"Scanner anomaly report:\n{json.dumps(scanner, indent=2)}\n\n"
                f"Investigator findings:\n{json.dumps(investigator, indent=2)}\n\n"
                f"Problem statement: {state.get('problem_statement', 'Not provided')}\n"
                f"Plant: {state.get('plant_id', '')} | Line: {state.get('line_id', '')}"
            )

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                max_tokens=1200,
                api_key=settings.openai_api_key,
            )
            raw = await safe_llm_call(
                llm,
                [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)],
            )
            result = parse_json_response(raw)
        except Exception as exc:
            _log("technician.llm_error", run_id=state["run_id"], error=str(exc))
            result = None

    if result is None:
        result = _fallback_result(state)

    pdf_path = generate_action_plan_pdf(
        run_id=state["run_id"],
        scanner_result=scanner,
        investigator=investigator,
        technician=result,
    )
    result["pdf_path"] = pdf_path

    _log("technician.done", run_id=state["run_id"], pdf_path=pdf_path, used_llm=settings.openai_api_key != "")
    return {
        **state,
        "technician_result": result,
        "final_report_path": pdf_path,
        "approval_status": "pending",
    }
