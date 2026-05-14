from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ConfidenceBreakdown(BaseModel):
    historical_similarity: float
    threshold_violation_strength: float
    maintenance_history_match: float
    data_completeness: float

    @model_validator(mode="after")
    def validate_total(self):
        total = (
            self.historical_similarity
            + self.threshold_violation_strength
            + self.maintenance_history_match
            + self.data_completeness
        )
        if total > 1.0001:
            raise ValueError("confidence breakdown must sum to <= 1.0")
        return self


class RootCauseHypothesis(BaseModel):
    hypothesis: str
    confidence: float
    confidence_breakdown: ConfidenceBreakdown
    supporting_evidence: list[str] = Field(default_factory=list)


class InvestigatorOutput(BaseModel):
    verdict: Literal["Stabilize", "Investigate", "Prevent Recurrence"]
    root_cause_hypotheses: list[RootCauseHypothesis]
    recommendations: dict[str, list[str]]
    compliance_reference: list[str] = Field(default_factory=list)
