"""Investigator agent: builds root-cause hypotheses and recommendations."""

from __future__ import annotations

import json
from typing import Any

from app.services.llm_utils import token_count


MAX_KB_TOKENS = 3000
CONFIDENCE_BREAKDOWN = {
    "historical_similarity": 0.35,
    "threshold_violation_strength": 0.25,
    "maintenance_history_match": 0.25,
    "data_completeness": 0.15,
}

LOCAL_KB = [
    {
        "source": "INC-2026-0312-LINE-B-004",
        "line_id": "LINE-B",
        "score": 0.94,
        "text": "Prior LINE-B low-pressure incident on PRESS-VALVE-23 was resolved by valve recalibration.",
    },
    {
        "source": "MNT-2026-0428-009",
        "line_id": "LINE-B",
        "score": 0.88,
        "text": "Maintenance noted actuator response delay on PRESS-VALVE-23 and recommended follow-up calibration.",
    },
    {
        "source": "SOP-LINE-B-PRESSURE-001",
        "line_id": "LINE-B",
        "score": 0.84,
        "text": "If pressure drops below 4.8 bar, reduce line speed, inspect the pressure valve, and verify sensor integrity.",
    },
]


def _log(event: str, **fields: Any) -> None:
    try:
        import structlog

        structlog.get_logger().info(event, **fields)
    except Exception:
        print(json.dumps({"event": event, **fields}, sort_keys=True))


def _build_kb_context(anomalies: list[dict[str, Any]], line_id: str) -> list[dict[str, Any]]:
    """Retrieve/deduplicate line-scoped context and cap it at 3,000 tokens."""
    del anomalies
    seen: set[str] = set()
    total = 0
    context: list[dict[str, Any]] = []

    for hit in LOCAL_KB:
        if hit["line_id"] not in (line_id, "") or hit["text"] in seen:
            continue
        cost = token_count(hit["text"])
        if total + cost > MAX_KB_TOKENS:
            break
        seen.add(hit["text"])
        context.append(hit)
        total += cost

    return context


def _primary_hypothesis(scanner_result: dict[str, Any]) -> str:
    anomaly_types = set(scanner_result.get("anomaly_type", []))
    if "LOW_PRESSURE" in anomaly_types:
        return "Pressure valve actuator drift caused low pressure and reduced output."
    if "TEMPERATURE_SPIKE" in anomaly_types:
        return "Thermal anomaly likely caused by lubrication or cooling degradation."
    if "HIGH_VIBRATION" in anomaly_types:
        return "Mechanical wear or bearing degradation is increasing vibration."
    if "DATA_GAP" in anomaly_types:
        return "Sensor signal interruption reduced data completeness and process visibility."
    return "Production conditions moved outside expected operating thresholds."


def _confidence(scanner_result: dict[str, Any]) -> float:
    severity = scanner_result.get("severity")
    if severity == "CRITICAL":
        return 0.86
    if severity == "HIGH":
        return 0.82
    return 0.68


async def investigator_node(state: dict[str, Any]) -> dict[str, Any]:
    scanner_result = state["scanner_result"]
    _log("investigator.start", run_id=state["run_id"], line_id=state.get("line_id"))

    retrieved_context = _build_kb_context([scanner_result], state["line_id"])
    result = {
        "verdict": "Stabilize" if scanner_result.get("severity") in ("HIGH", "CRITICAL") else "Investigate",
        "root_cause_hypotheses": [
            {
                "hypothesis": _primary_hypothesis(scanner_result),
                "confidence": _confidence(scanner_result),
                "confidence_breakdown": CONFIDENCE_BREAKDOWN,
                "supporting_evidence": [
                    *scanner_result.get("details", [])[:2],
                    *[item["text"] for item in retrieved_context[:2]],
                ],
            }
        ],
        "recommendations": {
            "stabilize": [
                "Reduce line speed or pause production if the anomaly persists.",
                "Notify shift supervisor and maintenance lead.",
            ],
            "investigate": [
                "Review current sensor trend against prior incidents and maintenance notes.",
                "Inspect the affected machine and verify sensor signal integrity.",
            ],
            "prevent_recurrence": [
                "Add automated alerting for early threshold drift.",
                "Update preventive maintenance checklist for the affected asset.",
            ],
        },
        "compliance_reference": [
            "Follow line-specific SOP before returning to full-speed production.",
            "Document investigation evidence under ISO 9001 controlled production requirements.",
        ],
    }

    _log(
        "investigator.done",
        run_id=state["run_id"],
        verdict=result["verdict"],
        context_count=len(retrieved_context),
    )
    return {**state, "retrieved_context": retrieved_context, "investigator_result": result}
