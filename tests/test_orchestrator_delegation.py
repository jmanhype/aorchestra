"""Tests for orchestrator delegation integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import DelegateAction, FinishAction


class TestDelegationFlow:
    """Test end-to-end delegation flow."""

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
    async def test_delegate_with_factory(self, orchestrator):
        """_delegate creates agent via factory and returns observation."""
        from aorchestra.orchestrator.state import OrchestratorState

        # Initialize state
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        action = DelegateAction(
            instruction="Calculate 1+1",
            context="Math needed",
            reasoning="Need computation",
        )

        # Mock factory
        mock_observation = Observation(
            result_summary="The answer is 2",
            artifacts={"result": 2},
        )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_observation)
        ) as mock_execute:
            result = await orchestrator._delegate(action)

            assert result.result_summary == "The answer is 2"
            mock_execute.assert_called_once()

            # Verify tuple structure
            call_args = mock_execute.call_args[0][0]
            assert call_args.instruction == "Calculate 1+1"
            assert "Math needed" in call_args.context

    @pytest.mark.asyncio
    async def test_delegate_includes_history_in_context(self, orchestrator):
        """_delegate includes relevant history in sub-agent context."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.core.tuples import AgentTuple

        # Create state with history
        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Search for X",
                model=orchestrator.model,
            ),
            observation=Observation(result_summary="Found: X is 42"),
        )
        state.add_delegation(delegation)
        orchestrator.state = state

        action = DelegateAction(
            instruction="Calculate X + 10",
            reasoning="Need math",
        )

        mock_obs = Observation(result_summary="52")
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ) as mock_execute:
            await orchestrator._delegate(action)

            # Verify context includes history
            call_args = mock_execute.call_args[0][0]
            assert "Relevant Previous Work" in call_args.context
            assert "Found: X is 42" in call_args.context

    @pytest.mark.asyncio
    async def test_delegate_handles_factory_errors(self, orchestrator):
        """_delegate captures factory errors in observation."""
        from aorchestra.orchestrator.state import OrchestratorState

        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        action = DelegateAction(
            instruction="Fail this",
            reasoning="Test error handling",
        )

        # Mock factory to raise exception
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(side_effect=Exception("API error"))
        ):
            result = await orchestrator._delegate(action)

            # Should return observation with error, not raise
            assert "Delegation failed" in result.result_summary
            assert "API error" in result.error_logs[0]

    @pytest.mark.asyncio
    async def test_filter_tools_returns_matching_tools(self, orchestrator):
        """_filter_tools returns tools matching requested names."""
        tools = orchestrator._filter_tools(["calculator", "search"])
        # "calculator" exists, "search" doesn't — should return calculator only
        names = {t.name for t in tools}
        assert "calculator" in names

    @pytest.mark.asyncio
    async def test_build_context_for_subagent_with_action_context(self, orchestrator):
        """_build_context_for_subagent includes action context."""
        from aorchestra.orchestrator.state import OrchestratorState

        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)
        action = DelegateAction(
            instruction="Task",
            context="Important context",
            reasoning="Reason",
        )

        context = orchestrator._build_context_for_subagent(action)
        assert "Important context" in context

    @pytest.mark.asyncio
    async def test_build_context_for_subagent_with_history(self, orchestrator):
        """_build_context_for_subagent includes recent history."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.core.tuples import AgentTuple

        state = OrchestratorState(goal="Test", max_steps=5)
        for i in range(5):
            delegation = Delegation(
                step=i,
                tuple=AgentTuple(
                    instruction=f"Task {i}",
                    model=orchestrator.model,
                ),
                observation=Observation(result_summary=f"Result {i}"),
            )
            state.add_delegation(delegation)
        orchestrator.state = state

        action = DelegateAction(instruction="New task", reasoning="Reason")
        context = orchestrator._build_context_for_subagent(action)

        # Should include some results from history
        assert "Result" in context
        # Recent items should be present (context curation includes recent + scored)
        assert "Result 4" in context
        # Context curation may include older items based on relevance scoring
        assert "**Relevant Previous Work:**" in context

    @pytest.mark.asyncio
    async def test_full_workflow_single_delegation(self, orchestrator):
        """Full workflow: delegate once then finish."""
        import json

        # Mock LLM to return delegate then finish
        delegate_response = MagicMock()
        delegate_response.choices = [MagicMock()]
        mock_tool_call_delegate = MagicMock()
        mock_tool_call_delegate.function.name = "delegate_subagent"
        mock_tool_call_delegate.function.arguments = json.dumps({
            "instruction": "Get current time",
            "reasoning": "Need time info",
        })
        delegate_response.choices[0].message.tool_calls = [mock_tool_call_delegate]

        finish_response = MagicMock()
        finish_response.choices = [MagicMock()]
        mock_tool_call_finish = MagicMock()
        mock_tool_call_finish.function.name = "finish_task"
        mock_tool_call_finish.function.arguments = json.dumps({
            "answer": "The current time is 10:30 AM",
            "reasoning": "Time retrieved",
        })
        finish_response.choices[0].message.tool_calls = [mock_tool_call_finish]

        # Mock factory
        mock_obs = Observation(result_summary="Time: 10:30 AM")

        # Patch the LLM client's completions.create method
        with patch.object(
            orchestrator.client.chat.completions, "create", new=AsyncMock(
                side_effect=[delegate_response, finish_response]
            )
        ):
            result = await orchestrator.run("What time is it?")

        assert result == "The current time is 10:30 AM"
        assert orchestrator.state.step == 1
        assert len(orchestrator.state.history) == 1
