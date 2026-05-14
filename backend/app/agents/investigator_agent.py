"""Investigator agent: builds root-cause hypotheses and recommendations."""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.services.llm_utils import parse_json_response, safe_llm_call, token_count


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

SYSTEM_PROMPT = """You are a manufacturing plant investigator agent. Analyse the scanner anomaly \
data and historical KB context provided, then return a concise root-cause analysis as strict JSON.

Respond with ONLY valid JSON — no markdown fences, no prose outside the JSON object.

Required schema:
{
  "verdict": "Stabilize" | "Investigate" | "Prevent Recurrence",
  "root_cause_hypotheses": [
    {
      "hypothesis": "<one specific sentence naming the root cause>",
      "confidence": <float 0.0–1.0>,
      "confidence_breakdown": {
        "historical_similarity": <float>,
        "threshold_violation_strength": <float>,
        "maintenance_history_match": <float>,
        "data_completeness": <float>
      },
      "supporting_evidence": ["<specific sensor reading or KB document reference>"]
    }
  ],
  "recommendations": {
    "stabilize": ["<immediate action>"],
    "investigate": ["<this-shift investigation step>"],
    "prevent_recurrence": ["<long-term preventive measure>"]
  },
  "compliance_reference": ["<SOP or ISO/OSHA standard reference>"]
}

Rules:
- confidence_breakdown values must sum to exactly 1.0
- Use "Stabilize" for HIGH or CRITICAL severity; "Investigate" for MEDIUM; "Prevent Recurrence" for recurring patterns
- Every recommendation and evidence item must be specific to the anomalies detected — no generic text
- Reference machine IDs, line IDs, and sensor values from the input where relevant
"""


def _log(event: str, **fields: Any) -> None:
    try:
        import structlog
        structlog.get_logger().info(event, **fields)
    except Exception:
        print(json.dumps({"event": event, **fields}, sort_keys=True))


def _build_kb_context(line_id: str) -> list[dict[str, Any]]:
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


def _fallback_result(scanner_result: dict[str, Any], retrieved_context: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "verdict": "Stabilize" if scanner_result.get("severity") in ("HIGH", "CRITICAL") else "Investigate",
        "root_cause_hypotheses": [
            {
                "hypothesis": _primary_hypothesis(scanner_result),
                "confidence": 0.86 if scanner_result.get("severity") == "CRITICAL" else 0.82,
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


async def investigator_node(state: dict[str, Any]) -> dict[str, Any]:
    scanner_result = state["scanner_result"]
    line_id = state.get("line_id", "")
    _log("investigator.start", run_id=state["run_id"], line_id=line_id)

    retrieved_context = _build_kb_context(line_id)
    result = None

    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage

            kb_text = "\n".join(
                f"[{h['source']}] {h['text']}" for h in retrieved_context
            ) or "No historical KB entries matched this line."

            user_msg = (
                f"Scanner anomaly report:\n{json.dumps(scanner_result, indent=2)}\n\n"
                f"Problem statement: {state.get('problem_statement', 'Not provided')}\n\n"
                f"Historical KB context (line {line_id}):\n{kb_text}"
            )

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                max_tokens=1500,
                api_key=settings.openai_api_key,
            )
            raw = await safe_llm_call(
                llm,
                [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_msg)],
            )
            result = parse_json_response(raw)
            # ensure confidence breakdown sums to 1.0
            breakdown = result.get("root_cause_hypotheses", [{}])[0].get("confidence_breakdown", {})
            total = sum(breakdown.values())
            if abs(total - 1.0) > 0.01:
                for key in breakdown:
                    breakdown[key] = round(breakdown[key] / total, 4)
        except Exception as exc:
            _log("investigator.llm_error", run_id=state["run_id"], error=str(exc))
            result = None

    if result is None:
        result = _fallback_result(scanner_result, retrieved_context)

    _log(
        "investigator.done",
        run_id=state["run_id"],
        verdict=result.get("verdict"),
        context_count=len(retrieved_context),
        used_llm=settings.openai_api_key != "",
    )
    return {**state, "retrieved_context": retrieved_context, "investigator_result": result}
