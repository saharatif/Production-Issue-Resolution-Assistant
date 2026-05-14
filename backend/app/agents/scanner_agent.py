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

    # group by line so every affected machine is represented
    lines_seen: dict[str, dict[str, Any]] = {}
    for reading, rule, sev in anomalies:
        lid = reading.get("line_id", "UNKNOWN")
        if lid not in lines_seen:
            lines_seen[lid] = {
                "line_id": lid,
                "machine_id": reading.get("machine_id"),
                "plant_id": reading.get("plant_id"),
                "anomaly_types": set(),
                "details": [],
                "max_severity": sev,
            }
        lines_seen[lid]["anomaly_types"].add(rule["anomaly_type"])
        lines_seen[lid]["details"].append(_detail_for(reading, rule))
        if SEVERITY_RANK[sev] > SEVERITY_RANK[lines_seen[lid]["max_severity"]]:
            lines_seen[lid]["max_severity"] = sev

    affected_lines = [
        {
            "line_id": v["line_id"],
            "machine_id": v["machine_id"],
            "anomaly_type": sorted(v["anomaly_types"]),
            "severity": v["max_severity"],
            "details": v["details"],
        }
        for v in lines_seen.values()
    ]

    # primary line = highest severity, then first encountered
    primary = max(affected_lines, key=lambda x: SEVERITY_RANK[x["severity"]])
    anomaly_types = sorted({t for line in affected_lines for t in line["anomaly_type"]})
    severity = max((line["severity"] for line in affected_lines), key=lambda s: SEVERITY_RANK[s])
    details = [d for line in affected_lines for d in line["details"]]

    return {
        "anomaly_detected": True,
        "plant_id": primary.get("machine_id") and lines_seen[primary["line_id"]]["plant_id"],
        "line_id": primary["line_id"],
        "machine_id": primary["machine_id"],
        "anomaly_type": anomaly_types,
        "severity": severity,
        "details": details,
        "affected_lines": affected_lines,
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
