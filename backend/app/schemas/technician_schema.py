from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ShiftHandoffNote(BaseModel):
    title: str
    summary: str
    current_status: str
    actions_completed: list[str] = Field(default_factory=list)
    open_actions: list[str] = Field(default_factory=list)


class MaintenanceRequest(BaseModel):
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    asset: str
    line_id: str
    request: str
    reason: str


class CorrectiveActionPlan(BaseModel):
    problem: str
    containment: str
    root_cause_analysis: str
    corrective_action: str
    preventive_action: str


class TechnicianOutput(BaseModel):
    shift_handoff_note: ShiftHandoffNote
    maintenance_request: MaintenanceRequest
    corrective_action_plan: CorrectiveActionPlan
    supplier_questions: list[str] = Field(default_factory=list)
    pdf_path: str | None = None
