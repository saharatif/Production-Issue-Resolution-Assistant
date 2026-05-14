"""Scanner agent: detects sensor anomalies and updates pipeline state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.llm_utils import token_count


MAX_BATCH_TOKENS = 2000
RULES_PATH = Path("data/scanner_rules.json")
SEVERITY_RANK = {"NONE": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _log(event: str, **fields: Any) -> None:
    try:
        import structlog

        structlog.get_logger().info(event, **fields)
    except Exception:
        print(json.dumps({"event": event, **fields}, sort_keys=True))


def _load_rules() -> list[dict[str, Any]]:
    with RULES_PATH.open("r", encoding="utf-8") as rules_file:
        return json.load(rules_file)["rules"]


def _trim_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cap incoming sensor JSON to 2,000 approximate tokens."""
    trimmed: list[dict[str, Any]] = []
    total = 0
    for reading in batch:
        cost = token_count(json.dumps(reading, sort_keys=True))
        if total + cost > MAX_BATCH_TOKENS:
            break
        trimmed.append(reading)
        total += cost
    return trimmed


def _violates_rule(value: Any, rule: dict[str, Any]) -> bool:
    condition = rule["condition"]
    if condition == "is_null":
        return value is None
    if value is None:
        return False
    if condition == ">":
        return float(value) > float(rule["threshold"])
    if condition == "<":
        return float(value) < float(rule["threshold"])
    return False


def _severity_for(value: Any, rule: dict[str, Any]) -> str:
    if rule["condition"] == "is_null":
        return "CRITICAL"

    critical = rule.get("critical_threshold")
    if critical is None or value is None:
        return str(rule.get("severity", "HIGH"))

    if rule["condition"] == ">" and float(value) > float(critical):
        return "CRITICAL"
    if rule["condition"] == "<" and float(value) < float(critical):
        return "CRITICAL"
    return str(rule.get("severity", "HIGH"))


def _detail_for(reading: dict[str, Any], rule: dict[str, Any]) -> str:
    metric = rule["metric"]
    value = reading.get(metric)
    if rule["condition"] == "is_null":
        return f"{metric} missing for {reading.get('line_id')} at {reading.get('timestamp')}."
    return (
        f"{metric}={value} breached {rule['condition']} {rule['threshold']} "
        f"for {reading.get('line_id')} / {reading.get('machine_id')}."
    )


def classify_batch(batch: list[dict[str, Any]]) -> dict[str, Any]:
    rules = _load_rules()
    anomalies: list[tuple[dict[str, Any], dict[str, Any], str]] = []

    for reading in batch:
        for rule in rules:
            if _violates_rule(reading.get(rule["metric"]), rule):
                anomalies.append((reading, rule, _severity_for(reading.get(rule["metric"]), rule)))

    if not anomalies:
        return {
            "anomaly_detected": False,
            "severity": "NONE",
            "details": [],
            "recommended_next_agent": None,
        }

    selected_reading = anomalies[0][0]
    anomaly_types = sorted({rule["anomaly_type"] for _, rule, _ in anomalies})
    severity = max((severity for _, _, severity in anomalies), key=lambda item: SEVERITY_RANK[item])
    details = [_detail_for(reading, rule) for reading, rule, _ in anomalies]

    return {
        "anomaly_detected": True,
        "plant_id": selected_reading.get("plant_id"),
        "line_id": selected_reading.get("line_id"),
        "machine_id": selected_reading.get("machine_id"),
        "anomaly_type": anomaly_types,
        "severity": severity,
        "details": details,
        "recommended_next_agent": "Investigator Agent",
    }


async def scanner_node(state: dict[str, Any]) -> dict[str, Any]:
    _log(
        "scanner.start",
        run_id=state["run_id"],
        line_id=state.get("line_id"),
        batch_size=len(state.get("raw_sensor_data", [])),
    )
    trimmed_batch = _trim_batch(state.get("raw_sensor_data", []))
    result = classify_batch(trimmed_batch)

    _log(
        "scanner.done",
        run_id=state["run_id"],
        anomaly_detected=result.get("anomaly_detected"),
        severity=result.get("severity"),
    )
    return {
        **state,
        "scanner_result": result,
        "has_anomaly": bool(result.get("anomaly_detected")),
    }
