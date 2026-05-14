from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    problem_statement: str = Field(default="")
    plant_id: str = Field(default="PLANT-01")
    line_id: str = Field(default="LINE-B")
    timeframe_start: str = Field(default="")
    timeframe_end: str = Field(default="")
    raw_sensor_data: list[dict[str, Any]] = Field(default_factory=list)
    scenario: str | None = None


class ApprovalRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    approver: str = Field(default="plant_manager")
    notes: str = Field(default="")
