"""Orchestrator state models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.cost import CostRecord


class Delegation(BaseModel):
    """Record of a single delegation step.

    Tracks the tuple used to create a sub-agent, the observation
    returned from execution, cost information, and metadata (step number, timestamp).
    """

    step: int = Field(
        ...,
        description="Step number when this delegation occurred",
        ge=0,
    )
    tuple: AgentTuple = Field(
        ...,
        description="The 4-tuple used to create the sub-agent",
    )
    observation: Observation = Field(
        ...,
        description="Observation returned from sub-agent execution",
    )
    cost_record: CostRecord = Field(
        ...,
        description="Cost record for this delegation (token usage and estimated cost)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of when the delegation completed",
    )


class OrchestratorState(BaseModel):
    """State of the orchestrator's execution.

    Tracks the current goal, step count, delegation history,
    execution constraints, and total cost.
    """

    goal: str = Field(
        ...,
        description="The overall goal the orchestrator is working toward",
    )
    step: int = Field(
        default=0,
        description="Current step number (starts at 0)",
        ge=0,
    )
    history: list[Delegation] = Field(
        default_factory=list,
        description="Chronological history of all delegations and observations",
    )
    max_steps: int = Field(
        default=20,
        description="Maximum number of delegation steps before forced termination",
        ge=1,
    )
    current_answer: Optional[str] = Field(
        default=None,
        description="Current best answer (accumulated from observations)",
    )
    total_cost_usd: float = Field(
        default=0.0,
        description="Total estimated cost in USD across all delegations",
        ge=0.0,
    )

    @property
    def is_finished(self) -> bool:
        """Check if orchestrator has reached max_steps."""
        return self.step >= self.max_steps

    def add_delegation(self, delegation: Delegation) -> None:
        """Add a delegation to history, increment step, and update total cost."""
        self.history.append(delegation)
        self.step += 1
        self.total_cost_usd += delegation.cost_record.estimated_cost_usd

    def get_cost_summary(self) -> dict:
        """Get cost summary across all delegations.

        Returns:
            Dict with total_cost_usd, total_tokens, delegation_count, model_breakdown
        """
        model_breakdown: dict[str, dict[str, float | int]] = {}
        total_tokens = 0

        for delegation in self.history:
            record = delegation.cost_record
            model_name = record.model_name
            total_tokens += record.total_tokens

            if model_name not in model_breakdown:
                model_breakdown[model_name] = {
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "calls": 0,
                }

            model_breakdown[model_name]["cost_usd"] += record.estimated_cost_usd
            model_breakdown[model_name]["tokens"] += record.total_tokens
            model_breakdown[model_name]["calls"] += 1

        return {
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": total_tokens,
            "delegation_count": len(self.history),
            "model_breakdown": model_breakdown,
        }
