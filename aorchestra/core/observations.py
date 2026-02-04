"""Observation models for sub-agent execution results."""

from typing import Any
from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Result of a SubAgent execution.

    Captures the outcome of executing a 4-tuple agent, including
    the result summary, any artifacts produced, and error logs.
    """

    result_summary: str = Field(
        ...,
        description="Human-readable summary of the agent's execution result",
    )
    artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured outputs produced during execution "
        "(files, data, intermediate results)",
    )
    error_logs: list[str] = Field(
        default_factory=list,
        description="Errors or warnings encountered during execution",
    )

    def add_error(self, error: str) -> None:
        """Add an error message to the error logs."""
        self.error_logs.append(error)

    def add_artifact(self, key: str, value: Any) -> None:
        """Add an artifact to the artifacts dictionary."""
        self.artifacts[key] = value
