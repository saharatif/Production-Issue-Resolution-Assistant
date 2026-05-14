"""Synthetic manufacturing sensor data for local demos and tests."""

from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Generator, Iterable


LINES = [
    {"plant_id": "PLANT-01", "line_id": "LINE-A", "machine_id": "CNC-MILL-11"},
    {"plant_id": "PLANT-01", "line_id": "LINE-B", "machine_id": "PRESS-VALVE-23"},
    {"plant_id": "PLANT-01", "line_id": "LINE-C", "machine_id": "SPINDLE-07"},
    {"plant_id": "PLANT-01", "line_id": "LINE-D", "machine_id": "COAT-SPRAY-04"},
]

NORMAL_RANGES = {
    "temperature_c": (68.0, 82.0),
    "pressure_bar": (5.2, 6.2),
    "vibration_mm_s": (1.5, 2.8),
    "output_units_per_hour": (900, 1050),
}

ANOMALY_PROFILES = {
    "LOW_PRESSURE": {
        "pressure_bar": (0.05, 0.15),
        "machine_status": "RUNNING_WITH_WARNING",
    },
    "TEMPERATURE_SPIKE": {
        "temperature_c": (280.0, 320.0),
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
    "DATA_GAP": None,
}

SCENARIO_TO_ANOMALY = {
    "pressure_drop": "LOW_PRESSURE",
    "temp_spike": "TEMPERATURE_SPIKE",
    "data_gap": "DATA_GAP",
    "high_vibration": "HIGH_VIBRATION",
    "output_drop": "OUTPUT_DROP",
}


@dataclass
class SensorReading:
    timestamp: str
    plant_id: str
    line_id: str
    machine_id: str
    temperature_c: float | None
    pressure_bar: float | None
    vibration_mm_s: float | None
    output_units_per_hour: int | None
    machine_status: str
    _anomaly_tag: str | None = field(default=None, repr=False)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normal_reading(line: dict[str, str]) -> SensorReading:
    return SensorReading(
        timestamp=_utc_timestamp(),
        plant_id=line["plant_id"],
        line_id=line["line_id"],
        machine_id=line["machine_id"],
        temperature_c=round(random.uniform(*NORMAL_RANGES["temperature_c"]), 2),
        pressure_bar=round(random.uniform(*NORMAL_RANGES["pressure_bar"]), 2),
        vibration_mm_s=round(random.uniform(*NORMAL_RANGES["vibration_mm_s"]), 2),
        output_units_per_hour=random.randint(*NORMAL_RANGES["output_units_per_hour"]),
        machine_status="RUNNING",
    )


def _apply_range(value_range: tuple[float, float] | tuple[int, int]) -> float | int:
    low, high = value_range
    if isinstance(low, int) and isinstance(high, int):
        return random.randint(low, high)
    return round(random.uniform(float(low), float(high)), 3)


def _inject_anomaly(reading: SensorReading, anomaly_tag: str) -> SensorReading:
    profile = ANOMALY_PROFILES[anomaly_tag]
    reading._anomaly_tag = anomaly_tag

    if profile is None:
        reading.temperature_c = None
        reading.pressure_bar = None
        reading.vibration_mm_s = None
        reading.output_units_per_hour = None
        reading.machine_status = "DATA_GAP"
        return reading

    for key, value in profile.items():
        if key == "machine_status":
            reading.machine_status = str(value)
        else:
            setattr(reading, key, _apply_range(value))
    return reading


def _public_dict(reading: SensorReading) -> dict[str, str | float | int | None]:
    payload = asdict(reading)
    payload.pop("_anomaly_tag", None)
    return payload


def generate_batch(anomaly_probability: float = 0.12) -> list[dict[str, str | float | int | None]]:
    """Return one reading per production line, with optional random anomalies."""
    if anomaly_probability < 0 or anomaly_probability > 1:
        raise ValueError("anomaly_probability must be between 0 and 1")

    batch = []
    for line in LINES:
        reading = _normal_reading(line)
        if random.random() < anomaly_probability:
            reading = _inject_anomaly(reading, random.choice(list(ANOMALY_PROFILES.keys())))
        batch.append(_public_dict(reading))
    return batch


def generate_stream(
    interval_seconds: float = 1.5,
    anomaly_probability: float = 0.12,
) -> Generator[list[dict[str, str | float | int | None]], None, None]:
    """Yield sensor batches forever for SSE endpoints or command-line demos."""
    while True:
        yield generate_batch(anomaly_probability=anomaly_probability)
        time.sleep(interval_seconds)


def generate_scenario_batch(scenario: str) -> list[dict[str, str | float | int | None]]:
    """Return a batch for a named frontend demo scenario."""
    if scenario in ("", "live"):
        return generate_batch()
    if scenario == "pressure_drop":
        return demo_scenario_line_b_pressure_drop()

    anomaly_tag = SCENARIO_TO_ANOMALY.get(scenario)
    if anomaly_tag is None:
        return generate_batch()

    batch = [_normal_reading(line) for line in LINES]
    target = next((r for r in batch if r.line_id == "LINE-B"), batch[0])
    _inject_anomaly(target, anomaly_tag)
    return [_public_dict(reading) for reading in batch]


def demo_scenario_line_b_pressure_drop() -> list[dict[str, str | float | int | None]]:
    """Deterministic demo where LINE-B always has LOW_PRESSURE behavior."""
    batch = [_normal_reading(line) for line in LINES]
    line_b = next(reading for reading in batch if reading.line_id == "LINE-B")
    _inject_anomaly(line_b, "LOW_PRESSURE")
    line_b.output_units_per_hour = random.randint(450, 620)
    return [_public_dict(reading) for reading in batch]


def serialize_sse_batch(batch: Iterable[dict[str, str | float | int | None]]) -> str:
    """Format a sensor batch as an SSE data frame."""
    import json

    return f"data: {json.dumps(list(batch))}\n\n"
