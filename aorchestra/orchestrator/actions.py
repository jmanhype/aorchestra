"""Action models for orchestrator decision-making."""

from pydantic import BaseModel, Field


class DelegateAction(BaseModel):
    """Action to delegate a subtask to a sub-agent.

    The LLM generates this action when it determines that a subtask
    should be delegated to a dynamically-created sub-agent.
    """

    instruction: str = Field(
        ...,
        description="Instruction for the sub-agent (what task to perform)",
    )
    context: str = Field(
        default="",
        description="Relevant context to pass to the sub-agent",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Names of tools to include (empty list = no tools)",
    )
    reasoning: str = Field(
        ...,
        description="Why this delegation is necessary",
    )


class FinishAction(BaseModel):
    """Action to finish with a final answer.

    The LLM generates this action when it determines that sufficient
    information has been gathered to answer the goal.
    """

    answer: str = Field(
        ...,
        description="The final answer to the orchestrator's goal",
    )
    reasoning: str = Field(
        ...,
        description="Why the task is complete and this answer is sufficient",
    )
