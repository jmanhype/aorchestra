"""Core 4-tuple agent abstraction: Φ = (Instruction, Context, Tools, Model)."""

from typing import Any
from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from aorchestra.models.config import ModelConfig


@dataclass
class AgentTuple:
    """A 4-tuple defining an agent: Φ = (Instruction, Context, Tools, Model).

    This is the foundational abstraction for all agents in AOrchestra.
    An orchestrator creates AgentTuples dynamically and uses AgentFactory
    to instantiate executable SubAgent instances.
    """

    instruction: str = Field(
        ...,
        description="The task instruction for the agent",
    )
    context: str = Field(
        default="",
        description="Relevant context information (previous observations, data, etc.)",
    )
    tools: list[Any] = Field(
        default_factory=list,
        description="List of tools available to the agent",
    )
    model: ModelConfig = Field(
        ...,
        description="Model configuration for LLM backend",
    )

    @field_validator("instruction")
    @classmethod
    def instruction_must_not_be_empty(cls, v: str) -> str:
        """Instruction must not be empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("instruction must not be empty")
        return v.strip()

    def build_prompt(self) -> str:
        """Build a prompt from instruction and context.

        Simple concatenation for item 001. Can be enhanced with
        templating in item 003.
        """
        if self.context:
            return f"{self.instruction}\n\nContext:\n{self.context}"
        return self.instruction
