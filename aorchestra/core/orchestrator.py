"""Orchestrator for task delegation and decision-making."""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator import prompts
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central orchestrator that delegates tasks to sub-agents.

    The orchestrator maintains a state history of all delegations and
    observations, and uses an LLM to decide at each step whether to
    Delegate (spawn a sub-agent) or Finish (return final answer).

    The orchestrator never directly executes environment actions -
    it only performs Delegate and Finish system actions.
    """

    def __init__(
        self,
        model: ModelConfig,
        factory: Optional[AgentFactory] = None,
        max_steps: int = 20,
    ):
        """Initialize the orchestrator.

        Args:
            model: Model configuration for the orchestrator's LLM.
            factory: AgentFactory for creating sub-agents. If None, creates default.
            max_steps: Maximum number of delegation steps (prevents infinite loops).
        """
        self.model = model
        self.factory = factory or AgentFactory()
        self.max_steps = max_steps
        self.client = AsyncOpenAI(**model.to_openai_kwargs())
        self.state: Optional[OrchestratorState] = None

    async def run(self, goal: str) -> str:
        """Run the orchestrator to complete a goal.

        Args:
            goal: The goal to accomplish.

        Returns:
            The final answer when the orchestrator finishes.

        Raises:
            RuntimeError: If max_steps is reached without finishing.
        """
        # Initialize state
        self.state = OrchestratorState(goal=goal, max_steps=self.max_steps)

        # Main decision loop
        while not self.state.is_finished:
            # Decide next action (using LLM)
            action = await self._decide_action()

            # Execute the action
            if isinstance(action, FinishAction):
                logger.info(f"Finishing with answer: {action.answer[:50]}...")
                return action.answer

            # Delegate action
            observation = await self._delegate(action)
            self._integrate_observation(action, observation)

        # Max steps reached
        raise RuntimeError(
            f"Orchestrator reached max_steps ({self.max_steps}) without finishing"
        )

    async def _decide_action(self) -> DelegateAction | FinishAction:
        """Decide the next action using the LLM.

        Constructs a prompt with the current goal and delegation history,
        then uses OpenAI function calling to get a structured action.

        Returns:
            Either a DelegateAction or FinishAction.

        Raises:
            ValueError: If LLM doesn't return a tool call.
        """
        # Build prompts
        system_prompt = prompts.build_system_prompt()
        user_prompt = prompts.build_user_prompt(self.state)

        logger.debug(f"Deciding action for step {self.state.step}")

        # Call LLM with function calling
        response = await self.client.chat.completions.create(
            model=self.model.name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_subagent",
                        "description": "Delegate a subtask to a sub-agent",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "instruction": {
                                    "type": "string",
                                    "description": "Instruction for the sub-agent",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "Relevant context to pass to the sub-agent",
                                },
                                "tools": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Tool names to include (empty = no tools)",
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "Why this delegation is necessary",
                                },
                            },
                            "required": ["instruction", "reasoning"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "finish_task",
                        "description": "Finish the task with a final answer",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "answer": {
                                    "type": "string",
                                    "description": "The final answer to the goal",
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "Why the task is complete",
                                },
                            },
                            "required": ["answer", "reasoning"],
                        },
                    },
                },
            ],
            tool_choice={"type": "required"},
            temperature=0.7,
        )

        # Parse the function call
        message = response.choices[0].message
        if not message.tool_calls:
            raise ValueError("LLM did not return a tool call")

        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        if function_name == "delegate_subagent":
            logger.debug(f"LLM chose to Delegate: {arguments['instruction'][:50]}...")
            return DelegateAction(**arguments)
        elif function_name == "finish_task":
            logger.debug(f"LLM chose to Finish: {arguments['answer'][:50]}...")
            return FinishAction(**arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")

    async def _delegate(self, action: DelegateAction) -> Observation:
        """Delegate a subtask to a sub-agent.

        Creates a 4-tuple from the DelegateAction, spawns a sub-agent
        via AgentFactory, and returns the observation.

        Args:
            action: The DelegateAction specifying the subtask.

        Returns:
            Observation from the sub-agent execution.
        """
        # Build context with relevant history
        context = self._build_context_for_subagent(action)

        # Filter tools (basic implementation for item 002)
        tools = self._filter_tools(action.tools)

        # Build AgentTuple
        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=context,
            tools=tools,
            model=self.model,  # Use same model (item 004 will add ModelRegistry)
        )

        logger.info(
            f"Delegating step {self.state.step}: {action.instruction[:50]}..."
        )

        # Execute via factory
        try:
            observation = await self.factory.create_and_execute(tuple_def)
            logger.info(
                f"Delegation completed: {observation.result_summary[:50]}..."
            )
        except Exception as e:
            # Capture unexpected errors
            logger.error(f"Delegation failed: {e}")
            observation = Observation(
                result_summary=f"Delegation failed: {str(e)}",
            )
            observation.add_error(str(e))

        return observation

    def _integrate_observation(
        self,
        action: DelegateAction,
        observation: Observation,
    ) -> None:
        """Integrate an observation into the orchestrator state.

        Creates a Delegation record and adds it to the history.

        Args:
            action: The DelegateAction that was executed.
            observation: The Observation returned from the sub-agent.
        """
        # Reconstruct the tuple (we need it for the Delegation record)
        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=self._build_context_for_subagent(action),
            tools=[],
            model=self.model,
        )

        delegation = Delegation(
            step=self.state.step,
            tuple=tuple_def,
            observation=observation,
        )

        self.state.add_delegation(delegation)

        logger.debug(
            f"State updated: step={self.state.step}, "
            f"history_length={len(self.state.history)}"
        )

    def _build_context_for_subagent(self, action: DelegateAction) -> str:
        """Build context string for a sub-agent.

        Includes the action's context plus relevant history.
        For item 002, include full history. Future items may summarize.

        Args:
            action: The DelegateAction being executed.

        Returns:
            Formatted context string.
        """
        parts = []

        # Add action-specific context
        if action.context:
            parts.append(action.context)

        # Add relevant history (last 3 observations for context)
        if self.state.history:
            parts.append("\n**Relevant Previous Work:**")
            recent_history = self.state.history[-3:]  # Last 3 delegations
            for delegation in recent_history:
                parts.append(
                    f"- {delegation.observation.result_summary}"
                )

        return "\n".join(parts) if parts else ""

    def _filter_tools(self, tool_names: list[str]) -> list:
        """Filter tools by name.

        For item 002, this is a simple placeholder. Item 003 will add
        ToolRegistry with intelligent tool selection.

        Args:
            tool_names: List of tool names to include.

        Returns:
            List of tool objects (empty list for item 002).
        """
        # Placeholder: Item 003 will implement ToolRegistry
        # For item 002, we don't have a tool registry yet
        # Return empty list (no tools) or all tools if requested
        if not tool_names:
            return []

        # TODO: Implement tool filtering in item 003
        logger.debug(f"Tool filtering not yet implemented, requested: {tool_names}")
        return []
