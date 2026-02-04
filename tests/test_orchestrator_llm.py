"""Tests for orchestrator LLM decision making."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord
from aorchestra.orchestrator.actions import DelegateAction, FinishAction


def _make_cost_record(model_name: str = "glm-4.7") -> CostRecord:
    """Helper to create a cost record."""
    return CostRecord(
        model_name=model_name,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.001,
    )


class TestLLMDecisionMaking:
    """Test LLM-based action selection."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=5)

    @pytest.mark.asyncio
    async def test_decide_action_parses_delegate_response(self, orchestrator):
        """_decide_action parses LLM delegate response."""
        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        # Create a proper mock for tool_calls
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "delegate_subagent"
        mock_tool_call.function.arguments = json.dumps({
            "instruction": "Calculate something",
            "context": "Math task",
            "tools": ["calculator"],
            "reasoning": "Need computation",
        })

        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            action = await orchestrator._decide_action()

        assert isinstance(action, DelegateAction)
        assert action.instruction == "Calculate something"
        assert action.tools == ["calculator"]

    @pytest.mark.asyncio
    async def test_decide_action_parses_finish_response(self, orchestrator):
        """_decide_action parses LLM finish response."""
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "finish_task"
        mock_tool_call.function.arguments = json.dumps({
            "answer": "The answer is 42",
            "reasoning": "Task complete",
        })

        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            action = await orchestrator._decide_action()

        assert isinstance(action, FinishAction)
        assert action.answer == "The answer is 42"

    @pytest.mark.asyncio
    async def test_decide_action_includes_history_in_prompt(self, orchestrator):
        """_decide_action includes delegation history in prompt."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.core.tuples import AgentTuple
        from aorchestra.core.observations import Observation

        # Create state with history
        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Previous task",
                model=orchestrator.model,
            ),
            observation=Observation(result_summary="Previous result"),
            cost_record=_make_cost_record(),
        )
        state.add_delegation(delegation)
        orchestrator.state = state

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "finish_task"
        mock_tool_call.function.arguments = json.dumps({
            "answer": "Done",
            "reasoning": "Complete",
        })

        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            await orchestrator._decide_action()

            # Verify prompt includes history
            call_args = orchestrator.client.chat.completions.create.call_args
            user_message = call_args[1]["messages"][1]["content"]
            assert "Previous Delegations" in user_message
            assert "Previous task" in user_message

    @pytest.mark.asyncio
    async def test_decide_action_raises_on_no_tool_call(self, orchestrator):
        """_decide_action raises ValueError if LLM doesn't return tool call."""
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        # Mock response without tool calls
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            with pytest.raises(ValueError, match="LLM did not return a tool call"):
                await orchestrator._decide_action()

    @pytest.mark.asyncio
    async def test_decide_action_raises_on_unknown_function(self, orchestrator):
        """_decide_action raises ValueError on unknown function name."""
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "unknown_function"
        mock_tool_call.function.arguments = json.dumps({})

        mock_response.choices[0].message.tool_calls = [mock_tool_call]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            with pytest.raises(ValueError, match="Unknown function: unknown_function"):
                await orchestrator._decide_action()


class TestPromptBuilders:
    """Test prompt building functions."""

    def test_build_system_prompt(self):
        """build_system_prompt returns non-empty string."""
        from aorchestra.orchestrator.prompts import build_system_prompt

        prompt = build_system_prompt()

        assert len(prompt) > 0
        assert "orchestrator" in prompt.lower()
        assert "Delegate" in prompt
        assert "Finish" in prompt

    def test_build_user_prompt_empty_history(self):
        """build_user_prompt formats goal without history."""
        from aorchestra.orchestrator.state import OrchestratorState
        from aorchestra.orchestrator.prompts import build_user_prompt

        state = OrchestratorState(goal="Test goal", max_steps=5)
        prompt = build_user_prompt(state)

        assert "**Goal:** Test goal" in prompt
        assert "**Current Step:** 0 / 5" in prompt
        assert "Previous Delegations" not in prompt

    def test_build_user_prompt_with_history(self):
        """build_user_prompt formats goal with history."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.orchestrator.prompts import build_user_prompt
        from aorchestra.core.tuples import AgentTuple
        from aorchestra.core.observations import Observation

        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Test task",
                model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
            ),
            observation=Observation(result_summary="Result"),
            cost_record=_make_cost_record(),
        )
        state.add_delegation(delegation)

        prompt = build_user_prompt(state)

        assert "Previous Delegations:" in prompt
        assert "Test task" in prompt
        assert "Result" in prompt
        assert "Step 0" in prompt

    def test_build_user_prompt_includes_errors(self):
        """build_user_prompt includes error logs in history."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.orchestrator.prompts import build_user_prompt
        from aorchestra.core.tuples import AgentTuple
        from aorchestra.core.observations import Observation

        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Test task",
                model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
            ),
            observation=Observation(
                result_summary="Partial success",
                error_logs=["API timeout"],
            ),
            cost_record=_make_cost_record(),
        )
        state.add_delegation(delegation)

        prompt = build_user_prompt(state)

        assert "Errors:" in prompt
        assert "API timeout" in prompt
