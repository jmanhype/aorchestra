"""Orchestrator state models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation


class Delegation(BaseModel):
    """Record of a single delegation step.

    Tracks the tuple used to create a sub-agent, the observation
    returned from execution, and metadata (step number, timestamp).
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
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of when the delegation completed",
    )


class OrchestratorState(BaseModel):
    """State of the orchestrator's execution.

    Tracks the current goal, step count, delegation history,
    and execution constraints.
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

    @property
    def is_finished(self) -> bool:
        """Check if orchestrator has reached max_steps."""
        return self.step >= self.max_steps

    def add_delegation(self, delegation: Delegation) -> None:
        """Add a delegation to history and increment step."""
        self.history.append(delegation)
        self.step += 1
