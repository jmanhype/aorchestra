"""Tests for AgentFactory."""

import pytest
from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool


class TestAgentFactory:
    """Test AgentFactory validation and creation."""

    @pytest.fixture
    def factory(self):
        """AgentFactory instance."""
        return AgentFactory()

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def valid_tuple(self, model_config):
        """Valid AgentTuple."""
        return AgentTuple(
            instruction="Test task",
            model=model_config,
        )

    def test_create_returns_subagent(self, factory, valid_tuple):
        """create() returns a SubAgent instance."""
        agent = factory.create(valid_tuple)
        assert agent.__class__.__name__ == "SubAgent"
        assert agent.tuple == valid_tuple

    def test_create_with_tools(self, factory, model_config):
        """create() works with tools."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            tools=[CalculatorTool()],
            model=model_config,
        )
        agent = factory.create(tuple_def)
        assert len(agent.tuple.tools) == 1

    def test_create_with_empty_instruction_raises_error(self, factory, model_config):
        """Empty instruction raises ValueError."""
        # This should be caught by Pydantic validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            tuple_def = AgentTuple(
                instruction="   ",
                model=model_config,
            )
            factory.create(tuple_def)

    def test_create_with_invalid_tool_raises_error(self, factory, model_config):
        """Invalid tool raises TypeError."""
        tuple_def = AgentTuple(
            instruction="Test",
            tools=[{"not": "a tool"}],
            model=model_config,
        )
        with pytest.raises(TypeError, match="Tool at index 0 is invalid"):
            factory.create(tuple_def)

    def test_create_with_invalid_model_name_raises_error(self, factory, model_config):
        """Empty model name raises ValueError."""
        tuple_def = AgentTuple(
            instruction="Test",
            model=ModelConfig(name="", api_base="https://api.z.ai/v1"),
        )
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            factory.create(tuple_def)

    def test_create_with_invalid_api_base_raises_error(self, factory):
        """Empty api_base raises ValueError (Pydantic validates this first)."""
        # Empty api_base fails Pydantic validation in ModelConfig
        # So it raises ValidationError, not ValueError from factory
        with pytest.raises(Exception):  # Pydantic ValidationError
            tuple_def = AgentTuple(
                instruction="Test",
                model=ModelConfig(name="glm-4.7", api_base=""),
            )
            factory.create(tuple_def)

    @pytest.mark.asyncio
    async def test_create_and_execute_convenience_method(self, factory, valid_tuple):
        """create_and_execute() creates agent and executes it."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from aorchestra.models.cost import CostRecord

        # Mock the SubAgent.execute method
        with patch("aorchestra.core.agents.SubAgent.execute") as mock_execute:
            mock_execute = AsyncMock()
            mock_observation = MagicMock()
            mock_observation.result_summary = "Test result"
            mock_cost_record = CostRecord(
                model_name="glm-4.7",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                estimated_cost_usd=0.0005,
            )
            mock_execute.return_value = (mock_observation, mock_cost_record)

            # Need to patch SubAgent to return our mock
            with patch("aorchestra.core.factory.SubAgent") as MockSubAgent:
                mock_agent_instance = MagicMock()
                mock_agent_instance.execute = mock_execute
                MockSubAgent.return_value = mock_agent_instance

                observation, cost_record = await factory.create_and_execute(valid_tuple)

        assert observation.result_summary == "Test result"
        assert isinstance(cost_record, CostRecord)
        assert cost_record.total_tokens == 15
