from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScannerOutput(BaseModel):
    anomaly_detected: bool
    plant_id: str | None = None
    line_id: str | None = None
    machine_id: str | None = None
    anomaly_type: list[str] = Field(default_factory=list)
    severity: Literal["NONE", "MEDIUM", "HIGH", "CRITICAL"]
    details: list[str] = Field(default_factory=list)
    recommended_next_agent: str | None = None
