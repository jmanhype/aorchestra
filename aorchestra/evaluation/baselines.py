"""Baseline agent implementations.

Item 005: SingleAgentBaseline and StaticRolesBaseline for comparison.
"""

from typing import Optional
from openai import AsyncOpenAI
from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord
from aorchestra.tools.registry import ToolRegistry
from aorchestra.core.agents import SubAgent


class SingleAgentBaseline:
    """Single-agent baseline (no delegation).

    Uses a single agent with all available tools to solve tasks directly.
    No orchestration or delegation - just a direct LLM call with tools.
    """

    def __init__(
        self,
        model: ModelConfig,
        tool_registry: ToolRegistry,
    ):
        """Initialize the single-agent baseline.

        Args:
            model: Model configuration for the agent
            tool_registry: Tool registry to get tool objects from names
        """
        self.model = model
        self.tool_registry = tool_registry
        self.factory = AgentFactory()

    async def solve(
        self,
        goal: str,
        tool_names: list[str],
        context: str = "",
    ) -> tuple[str, CostRecord]:
        """Solve a goal using a single agent with specified tools.

        Args:
            goal: The task goal/instruction
            tool_names: List of tool names to make available
            context: Optional context information

        Returns:
            Tuple of (answer, cost_record)

        Raises:
            ValueError: If any tool name is not found in registry
        """
        # Get tool objects from registry
        tools = []
        for tool_name in tool_names:
            tool = self.tool_registry.get(tool_name)
            if tool is None:
                raise ValueError(f"Tool not found in registry: {tool_name}")
            tools.append(tool)

        # Build AgentTuple
        tuple_def = AgentTuple(
            instruction=goal,
            context=context,
            tools=tools,
            model=self.model,
        )

        # Execute agent
        observation, cost_record = await self.factory.create_and_execute(tuple_def)

        # Return answer from observation
        answer = observation.result_summary
        return answer, cost_record


class StaticRolesBaseline:
    """Static-roles baseline (fixed sub-agents).

    Creates 4 fixed sub-agents with predefined roles and tools:
    - math_agent: CalculatorTool for arithmetic tasks
    - code_agent: CodeExecuteTool for code execution
    - research_agent: WebSearchMockTool for information retrieval
    - planning_agent: FileReadTool for file-based planning

    Uses LLM with temperature=0 to select the appropriate agent type.
    """

    # Valid agent types
    VALID_AGENT_TYPES = {"math", "code", "research", "planning"}

    def __init__(
        self,
        model: ModelConfig,
        tool_registry: ToolRegistry,
    ):
        """Initialize the static-roles baseline.

        Args:
            model: Model configuration for all agents
            tool_registry: Tool registry to get tool objects from names
        """
        self.model = model
        self.tool_registry = tool_registry
        self.agents = self._create_fixed_agents()
        self.client = AsyncOpenAI(
            api_key=model.api_key or "dummy",
            base_url=model.api_base,
        )

    def _create_fixed_agents(self) -> dict[str, SubAgent]:
        """Create fixed sub-agents for each role.

        Returns:
            Dictionary mapping agent type to SubAgent instances
        """
        agents = {}

        # Math agent with calculator tool
        math_tool = self.tool_registry.get("calculator")
        if math_tool:
            math_tuple = AgentTuple(
                instruction="Solve the task",
                context="You are a math expert. Use the calculator tool for arithmetic operations.",
                tools=[math_tool],
                model=self.model,
            )
            agents["math"] = SubAgent(math_tuple)

        # Code agent with code_execute tool
        code_tool = self.tool_registry.get("code_execute")
        if code_tool:
            code_tuple = AgentTuple(
                instruction="Solve the task",
                context="You are a coding expert. Use the code_execute tool to run Python code.",
                tools=[code_tool],
                model=self.model,
            )
            agents["code"] = SubAgent(code_tuple)

        # Research agent with web_search_mock tool
        research_tool = self.tool_registry.get("web_search_mock")
        if research_tool:
            research_tuple = AgentTuple(
                instruction="Solve the task",
                context="You are a research expert. Use the web_search_mock tool to find information.",
                tools=[research_tool],
                model=self.model,
            )
            agents["research"] = SubAgent(research_tuple)

        # Planning agent with file_read tool
        planning_tool = self.tool_registry.get("file_read")
        if planning_tool:
            planning_tuple = AgentTuple(
                instruction="Solve the task",
                context="You are a planning expert. Use the file_read tool to read files.",
                tools=[planning_tool],
                model=self.model,
            )
            agents["planning"] = SubAgent(planning_tuple)

        return agents

    async def _select_agent_type(self, goal: str) -> str:
        """Select the appropriate agent type using LLM.

        Args:
            goal: The task goal/instruction

        Returns:
            Selected agent type (math, code, research, or planning)
        """
        prompt = f"""You are an agent selector. Choose the most appropriate agent type for this task.

Valid agent types:
- math: For arithmetic calculations, mathematical operations, numerical tasks
- code: For writing and executing Python code, programming tasks
- research: For searching information, retrieving knowledge, answering questions
- planning: For file operations, multi-step planning, coordination tasks

Task: {goal}

Respond with ONLY the agent type name (math, code, research, or planning). Do not include any other text."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model.name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=10,
            )

            agent_type = response.choices[0].message.content.strip().lower()

            # Validate and return
            if agent_type in self.VALID_AGENT_TYPES:
                return agent_type
            else:
                # Default to math agent for invalid selections
                return "math"

        except Exception as e:
            # On any error, default to math agent
            return "math"

    async def solve(self, goal: str, tool_names: list[str], context: str = "") -> tuple[str, CostRecord]:
        """Solve a goal using the selected fixed sub-agent.

        Args:
            goal: The task goal/instruction
            tool_names: List of tool names (ignored, agents have fixed tools)
            context: Optional context information (ignored, agents have fixed context)

        Returns:
            Tuple of (answer, cost_record)
        """
        # Select agent type using LLM
        agent_type = await self._select_agent_type(goal)

        # Get the agent
        agent = self.agents.get(agent_type)
        if agent is None:
            # Fallback to math agent if selected agent not available
            agent_type = "math"
            agent = self.agents.get(agent_type)

        if agent is None:
            raise RuntimeError("No agents available in StaticRolesBaseline")

        # Update the agent's instruction with the goal
        agent.tuple.instruction = goal

        # Execute the agent
        observation, cost_record = await agent.execute()

        # Return answer from observation
        answer = observation.result_summary
        return answer, cost_record
