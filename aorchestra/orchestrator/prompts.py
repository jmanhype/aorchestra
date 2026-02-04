"""Prompts and context construction for orchestrator LLM."""

from aorchestra.orchestrator.state import OrchestratorState


def build_system_prompt() -> str:
    """Build the system prompt for the orchestrator LLM.

    The system prompt explains the orchestrator's role and the two
    available actions (Delegate and Finish).
    """
    return """You are an orchestrator responsible for completing a complex goal by delegating subtasks to specialized sub-agents.

You have two actions available:

1. **Delegate**: Create a sub-agent to perform a specific subtask. Use this when:
   - The goal requires specialized work you cannot do directly
   - You need information gathering, computation, or external interaction
   - The goal can be decomposed into smaller steps

2. **Finish**: Return a final answer to the goal. Use this when:
   - You have sufficient information to answer the goal completely
   - Further delegations would not add value
   - The goal has been accomplished

IMPORTANT:
- You never execute tasks directly - you only delegate and finish
- Each delegation should have a clear, specific instruction
- Provide reasoning for your decision to help with transparency
- Be efficient - don't delegate unnecessarily
- Finish as soon as you have enough information to answer the goal
"""


def build_user_prompt(state: OrchestratorState) -> str:
    """Build the user prompt with current context.

    Includes the goal and relevant history of delegations and observations.

    Args:
        state: Current orchestrator state.

    Returns:
        Formatted prompt string.
    """
    lines = [
        f"**Goal:** {state.goal}",
        f"**Current Step:** {state.step} / {state.max_steps}",
    ]

    if state.history:
        lines.append("\n**Previous Delegations:**")
        for i, delegation in enumerate(state.history, 1):
            lines.append(f"\n{i}. Step {delegation.step}")
            lines.append(f"   - Instruction: {delegation.tuple.instruction}")
            lines.append(f"   - Result: {delegation.observation.result_summary}")

            # Include errors if any
            if delegation.observation.error_logs:
                lines.append(f"   - Errors: {', '.join(delegation.observation.error_logs)}")

    lines.append("\n**What is your next action?**")

    return "\n".join(lines)
