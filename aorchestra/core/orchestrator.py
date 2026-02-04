"""Orchestrator for task delegation and decision-making."""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord, CostTracker
from aorchestra.models.registry import ModelRegistry, get_builtin_models
from aorchestra.orchestrator import prompts, context
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.tools import ToolRegistry, get_builtin_tools_metadata

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central orchestrator that delegates tasks to sub-agents.

    The orchestrator maintains a state history of all delegations and
    observations, and uses an LLM to decide at each step whether to
    Delegate (spawn a sub-agent) or Finish (return final answer).

    The orchestrator never directly executes environment actions -
    it only performs Delegate and Finish system actions.

    Item 003: Enhanced with ToolRegistry and intelligent context curation.
    Item 004: Enhanced with ModelRegistry and cost-aware model routing.
    """

    def __init__(
        self,
        model: ModelConfig,
        factory: Optional[AgentFactory] = None,
        tool_registry: Optional[ToolRegistry] = None,
        model_registry: Optional[ModelRegistry] = None,
        lambda_param: float = 0.5,
        max_steps: int = 20,
    ):
        """Initialize the orchestrator.

        Args:
            model: Model configuration for the orchestrator's LLM.
            factory: AgentFactory for creating sub-agents. If None, creates default.
            tool_registry: ToolRegistry for managing tools. If None, creates default
                with built-in tools (Item 003).
            model_registry: ModelRegistry for model selection (Item 004). If None,
                creates default with built-in models.
            lambda_param: Cost-performance trade-off parameter (Item 004). 0.0 = prefer
                accuracy, 1.0 = prefer cost. Default: 0.5 (balanced).
            max_steps: Maximum number of delegation steps (prevents infinite loops).
        """
        self.model = model
        self.factory = factory or AgentFactory()
        self.max_steps = max_steps
        self.lambda_param = lambda_param
        self.client = AsyncOpenAI(**model.to_openai_kwargs())
        self.state: Optional[OrchestratorState] = None

        # Initialize tool registry (Item 003)
        self.tool_registry = tool_registry or self._create_default_tool_registry()

        # Initialize model registry and cost tracker (Item 004)
        self.model_registry = model_registry or self._create_default_model_registry()
        self.cost_tracker = CostTracker()

    def _create_default_tool_registry(self) -> ToolRegistry:
        """Create default ToolRegistry with built-in tools.

        Returns:
            ToolRegistry with all built-in tools registered.
        """
        registry = ToolRegistry()

        # Register all built-in tools
        for metadata, tool_class in get_builtin_tools_metadata():
            tool = tool_class()
            registry.register(tool, metadata)
            logger.info(f"Registered built-in tool: {tool.name}")

        return registry

    def _create_default_model_registry(self) -> ModelRegistry:
        """Create default ModelRegistry with built-in models.

        Returns:
            ModelRegistry with flash, standard, and premium models registered.
        """
        registry = ModelRegistry()

        # Register all built-in models
        for config, tier in get_builtin_models():
            registry.register(config, tier)
            logger.info(f"Registered built-in model: {config.name} ({tier.tier})")

        return registry

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
                # Log total cost on finish (Item 004)
                total_tokens = self.cost_tracker.get_total_tokens()
                total_cost = self.cost_tracker.get_total_cost()
                logger.info(
                    f"Finishing with answer: {action.answer[:50]}... "
                    f"(total_tokens={total_tokens}, total_cost=${total_cost:.6f})"
                )
                return action.answer

            # Delegate action
            observation, cost_record = await self._delegate(action)
            self._integrate_observation(action, observation, cost_record)

        # Max steps reached - log total cost (Item 004)
        total_tokens = self.cost_tracker.get_total_tokens()
        total_cost = self.cost_tracker.get_total_cost()
        logger.info(
            f"Max steps reached without finishing "
            f"(total_tokens={total_tokens}, total_cost=${total_cost:.6f})"
        )

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

    async def _delegate(self, action: DelegateAction) -> tuple[Observation, CostRecord]:
        """Delegate a subtask to a sub-agent.

        Creates a 4-tuple from the DelegateAction, spawns a sub-agent
        via AgentFactory, and returns the observation and cost record.

        Item 004: Uses ModelRegistry to select model based on task complexity
        and tracks token usage and cost.

        Args:
            action: The DelegateAction specifying the subtask.

        Returns:
            Tuple of (Observation, CostRecord) from the sub-agent execution.
        """
        from aorchestra.models.cost import ModelSelectionCriteria
        from aorchestra.orchestrator.selection import estimate_complexity

        # Build context with relevant history
        context_str = self._build_context_for_subagent(action)

        # Filter tools (basic implementation for item 002)
        tools = self._filter_tools(action.tools)

        # Estimate complexity for model selection (Item 004)
        complexity = estimate_complexity(
            instruction=action.instruction,
            tools=[t.name for t in tools],
            context_length=len(context_str),
        )

        # Select model based on complexity and lambda (Item 004)
        criteria = ModelSelectionCriteria(
            complexity=complexity,
            lambda_param=self.lambda_param,
        )
        selected_model = self.model_registry.select_model(criteria)

        # Log model selection
        tier_info = self.model_registry.get_tier(selected_model.name)
        tier_name = tier_info.tier if tier_info else "unknown"
        logger.info(
            f"Selected model: {selected_model.name} (tier={tier_name}, "
            f"complexity={complexity:.2f}, lambda={self.lambda_param})"
        )

        # Build AgentTuple with selected model
        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=context_str,
            tools=tools,
            model=selected_model,  # Item 004: Use selected model
        )

        logger.info(
            f"Delegating step {self.state.step}: {action.instruction[:50]}..."
        )

        # Execute via factory
        try:
            observation, cost_record = await self.factory.create_and_execute(tuple_def)

            # Recalculate cost with actual model tier rates (Item 004)
            tier = self.model_registry.get_tier(selected_model.name)
            if tier:
                actual_cost = (
                    (cost_record.prompt_tokens / 1000) * tier.cost_per_1k_input
                    + (cost_record.completion_tokens / 1000) * tier.cost_per_1k_output
                )
                cost_record.estimated_cost_usd = actual_cost

            # Track cost
            self.cost_tracker.track(cost_record)

            logger.info(
                f"Delegation completed: {observation.result_summary[:50]}... "
                f"(tokens={cost_record.total_tokens}, cost=${cost_record.estimated_cost_usd:.6f})"
            )
        except Exception as e:
            # Capture unexpected errors
            logger.error(f"Delegation failed: {e}")
            observation = Observation(
                result_summary=f"Delegation failed: {str(e)}",
            )
            observation.add_error(str(e))
            # Create zero cost record for failed delegation
            from aorchestra.models.cost import CostRecord
            cost_record = CostRecord(
                model_name=selected_model.name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
            )

        return observation, cost_record

    def _integrate_observation(
        self,
        action: DelegateAction,
        observation: Observation,
        cost_record: CostRecord,
    ) -> None:
        """Integrate an observation into the orchestrator state.

        Creates a Delegation record and adds it to the history.

        Item 004: Now includes cost_record parameter and tracks costs.

        Args:
            action: The DelegateAction that was executed.
            observation: The Observation returned from the sub-agent.
            cost_record: CostRecord with token usage and estimated cost.
        """
        # Reconstruct the tuple using same model selection logic as _delegate (Item 004)
        from aorchestra.models.cost import ModelSelectionCriteria
        from aorchestra.orchestrator.selection import estimate_complexity

        context_str = self._build_context_for_subagent(action)

        # Estimate complexity and select model (same as _delegate)
        complexity = estimate_complexity(
            instruction=action.instruction,
            tools=[],
            context_length=len(context_str),
        )

        criteria = ModelSelectionCriteria(
            complexity=complexity,
            lambda_param=self.lambda_param,
        )
        selected_model = self.model_registry.select_model(criteria)

        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=context_str,
            tools=[],
            model=selected_model,  # Item 004: Use selected model
        )

        delegation = Delegation(
            step=self.state.step,
            tuple=tuple_def,
            observation=observation,
            cost_record=cost_record,  # Item 004: Include cost record
        )

        self.state.add_delegation(delegation)

        logger.debug(
            f"State updated: step={self.state.step}, "
            f"history_length={len(self.state.history)}, "
            f"total_cost=${self.state.total_cost_usd:.6f}"
        )

    def _build_context_for_subagent(self, action: DelegateAction) -> str:
        """Build context string for a sub-agent.

        Item 003: Enhanced with intelligent context curation.
        Uses keyword extraction and relevance scoring to select
        relevant history items.

        Args:
            action: The DelegateAction being executed.

        Returns:
            Formatted context string.
        """
        # Extract keywords from instruction for relevance scoring
        keywords = context.extract_keywords_from_instruction(action.instruction)

        # Build context using curation logic
        return context.build_context_for_subtask(
            action_context=action.context,
            history=self.state.history if self.state else [],
            keywords=keywords,
            max_history_items=3,
        )

    def _filter_tools(self, tool_names: list[str]) -> list:
        """Filter tools by name or intelligently select based on task.

        Item 003: Uses ToolRegistry for tool selection.

        If LLM specified tool names, returns those tools.
        Otherwise, uses intelligent selection based on task keywords.

        Args:
            tool_names: List of tool names to include.

        Returns:
            List of tool objects.
        """
        # If LLM specified tool names, get those tools
        if tool_names:
            tools = []
            for name in tool_names:
                tool = self.tool_registry.get(name)
                if tool:
                    tools.append(tool)
                else:
                    logger.warning(f"Tool not found in registry: {name}")
            return tools

        # Otherwise, select tools intelligently based on task keywords
        # Extract keywords from current instruction (if state exists)
        if self.state and self.state.history:
            # Use most recent instruction for keyword extraction
            recent_instruction = self.state.history[-1].tuple.instruction
            keywords = context.extract_keywords_from_instruction(recent_instruction)
        else:
            keywords = []

        # Create selection criteria
        from aorchestra.tools import ToolSelectionCriteria

        criteria = ToolSelectionCriteria(
            keywords=keywords,
            max_tools=5,  # Limit number of tools for efficiency
        )

        # Select tools from registry
        selected = self.tool_registry.select_tools(criteria)

        logger.debug(
            f"Selected {len(selected)} tools for delegation: "
            f"{[t.name for t in selected]}"
        )

        return selected
