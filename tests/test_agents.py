"""Tests for SubAgent execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.agents import SubAgent
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord
from aorchestra.tools.mock import EchoTool, CalculatorTool


class TestSubAgent:
    """Test SubAgent execution logic."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def simple_tuple(self, model_config):
        """Simple tuple without tools."""
        return AgentTuple(
            instruction="Say hello",
            model=model_config,
        )

    @pytest.fixture
    def tuple_with_tools(self, model_config):
        """Tuple with echo and calculator tools."""
        return AgentTuple(
            instruction="Use tools",
            tools=[EchoTool(), CalculatorTool()],
            model=model_config,
        )

    def test_subagent_initialization(self, simple_tuple):
        """SubAgent initializes with AgentTuple."""
        agent = SubAgent(simple_tuple)
        assert agent.tuple == simple_tuple

    @pytest.mark.asyncio
    async def test_execute_without_tools(self, simple_tuple):
        """Execute with simple prompt, no tools."""
        # Mock OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.choices[0].message.tool_calls = None

        # Mock usage data
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 5
        mock_usage.total_tokens = 15
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = SubAgent(simple_tuple, client=mock_client)
        observation, cost_record = await agent.execute()

        assert isinstance(observation, Observation)
        assert observation.result_summary == "Hello, world!"
        assert observation.error_logs == []
        assert isinstance(cost_record, CostRecord)
        assert cost_record.prompt_tokens == 10
        assert cost_record.completion_tokens == 5

    @pytest.mark.asyncio
    async def test_execute_with_tools(self, tuple_with_tools):
        """Execute with tools that get invoked."""
        # Mock OpenAI response with tool call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        # Create a proper mock tool_call structure
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "echo"
        mock_tool_call.function.arguments = '{"message": "test"}'
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        # Mock usage data
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 20
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = SubAgent(tuple_with_tools, client=mock_client)
        observation, cost_record = await agent.execute()

        assert isinstance(observation, Observation)
        assert "echo" in observation.result_summary
        assert observation.artifacts["echo"] == "Echo: test"
        assert isinstance(cost_record, CostRecord)

    @pytest.mark.asyncio
    async def test_execute_with_tool_error(self, tuple_with_tools):
        """Tool execution errors are captured in error_logs."""
        # Mock OpenAI response with calculator tool call (divide by zero)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        # Create a proper mock tool_call structure
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "calculator"
        mock_tool_call.function.arguments = '{"operation": "divide", "a": 5, "b": 0}'
        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        # Mock usage data
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 20
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        agent = SubAgent(tuple_with_tools, client=mock_client)
        observation, cost_record = await agent.execute()

        assert isinstance(observation, Observation)
        assert len(observation.error_logs) > 0
        assert "calculator" in observation.error_logs[0]
        assert isinstance(cost_record, CostRecord)

    @pytest.mark.asyncio
    async def test_execute_handles_llm_errors(self, simple_tuple):
        """LLM errors are caught and returned in Observation."""
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        agent = SubAgent(simple_tuple, client=mock_client)
        observation, cost_record = await agent.execute()

        assert isinstance(observation, Observation)
        assert "Execution failed" in observation.result_summary
        assert len(observation.error_logs) > 0
        assert isinstance(cost_record, CostRecord)
        assert cost_record.total_tokens == 0  # Zero cost on error
        assert cost_record.estimated_cost_usd == 0.0

    def test_build_prompt_without_context(self, simple_tuple):
        """Prompt building without context."""
        agent = SubAgent(simple_tuple)
        prompt = agent.tuple.build_prompt()
        assert prompt == "Say hello"

    def test_build_prompt_with_context(self, model_config):
        """Prompt building with context."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            context="Numbers: 1, 2, 3",
            model=model_config,
        )
        agent = SubAgent(tuple_def)
        prompt = agent.tuple.build_prompt()
        assert "Calculate" in prompt
        assert "Numbers: 1, 2, 3" in prompt

    def test_find_tool_by_name(self, tuple_with_tools):
        """Can find tools by name."""
        agent = SubAgent(tuple_with_tools)
        echo_tool = agent._find_tool("echo")
        assert echo_tool is not None
        assert echo_tool.name == "echo"

    def test_find_nonexistent_tool_returns_none(self, tuple_with_tools):
        """Finding nonexistent tool returns None."""
        agent = SubAgent(tuple_with_tools)
        tool = agent._find_tool("nonexistent")
        assert tool is None
