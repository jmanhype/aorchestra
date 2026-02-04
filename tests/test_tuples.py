"""Tests for AgentTuple."""

import pytest
from pydantic import ValidationError
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig


class TestAgentTuple:
    """Test AgentTuple validation and behavior."""

    @pytest.fixture
    def model_config(self):
        """Default model config for tests."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    def test_create_agent_tuple_minimal(self, model_config):
        """AgentTuple with instruction and model only."""
        tuple_def = AgentTuple(
            instruction="Solve this task",
            model=model_config,
        )
        assert tuple_def.instruction == "Solve this task"
        assert tuple_def.context == ""
        assert tuple_def.tools == []
        assert tuple_def.model == model_config

    def test_create_agent_tuple_full(self, model_config):
        """AgentTuple with all fields specified."""
        tuple_def = AgentTuple(
            instruction="Calculate sum",
            context="Numbers: 1, 2, 3",
            tools=["calculator"],
            model=model_config,
        )
        assert tuple_def.context == "Numbers: 1, 2, 3"
        assert tuple_def.tools == ["calculator"]

    def test_empty_instruction_raises_error(self, model_config):
        """instruction must not be empty."""
        with pytest.raises(ValidationError) as exc:
            AgentTuple(instruction="", model=model_config)
        assert "instruction must not be empty" in str(exc.value)

    def test_whitespace_instruction_is_trimmed(self, model_config):
        """Leading/trailing whitespace in instruction is trimmed."""
        tuple_def = AgentTuple(
            instruction="  Solve task  ",
            model=model_config,
        )
        assert tuple_def.instruction == "Solve task"

    def test_build_prompt_without_context(self, model_config):
        """build_prompt() returns just instruction when no context."""
        tuple_def = AgentTuple(
            instruction="Task description",
            model=model_config,
        )
        assert tuple_def.build_prompt() == "Task description"

    def test_build_prompt_with_context(self, model_config):
        """build_prompt() combines instruction and context."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            context="Numbers: 1, 2, 3",
            model=model_config,
        )
        prompt = tuple_def.build_prompt()
        assert "Calculate" in prompt
        assert "Numbers: 1, 2, 3" in prompt

    def test_serialization(self, model_config):
        """AgentTuple can be serialized to/from JSON."""
        tuple_def = AgentTuple(
            instruction="Task",
            context="Context",
            tools=["tool1"],
            model=model_config,
        )
        # Pydantic dataclasses support model_dump_json()
        import json
        from pydantic import TypeAdapter

        adapter = TypeAdapter(AgentTuple)
        json_str = adapter.dump_json(tuple_def)
        restored = adapter.validate_json(json_str)
        assert restored.instruction == tuple_def.instruction
        assert restored.context == tuple_def.context
