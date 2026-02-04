"""Tests for Orchestrator class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import FinishAction


class TestOrchestrator:
    """Test Orchestrator state machine."""

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

    def test_initialization(self, model_config):
        """Orchestrator initializes correctly."""
        orch = Orchestrator(model=model_config, max_steps=10)
        assert orch.model == model_config
        assert orch.max_steps == 10
        assert orch.state is None
        assert orch.factory is not None

    def test_initialization_with_custom_factory(self, model_config):
        """Orchestrator can accept a custom factory."""
        from aorchestra.core.factory import AgentFactory
        custom_factory = AgentFactory()
        orch = Orchestrator(model=model_config, factory=custom_factory)
        assert orch.factory == custom_factory

    @pytest.mark.asyncio
    async def test_run_returns_finish_action_answer(self, orchestrator):
        """run() returns the answer from FinishAction."""
        # Mock _decide_action to return FinishAction immediately
        async def mock_decide():
            return FinishAction(answer="Test answer", reasoning="Done")
        orchestrator._decide_action = mock_decide
        result = await orchestrator.run("Test goal")
        assert result == "Test answer"

    @pytest.mark.asyncio
    async def test_run_initializes_state(self, orchestrator):
        """run() initializes orchestrator state."""
        # Mock _decide_action to return FinishAction immediately
        async def mock_decide():
            return FinishAction(answer="Done", reasoning="Done")
        orchestrator._decide_action = mock_decide
        await orchestrator.run("Test goal")
        assert orchestrator.state is not None
        assert orchestrator.state.goal == "Test goal"
        assert orchestrator.state.max_steps == 5

    @pytest.mark.asyncio
    async def test_max_steps_raises_error(self, orchestrator):
        """Max steps reached raises RuntimeError."""
        # Mock _decide_action to always delegate
        async def mock_delegate():
            from aorchestra.orchestrator.actions import DelegateAction
            return DelegateAction(
                instruction="Test",
                reasoning="Test",
            )

        orchestrator._decide_action = mock_delegate

        # Mock _delegate to return observation
        mock_obs = Observation(result_summary="Done")
        orchestrator._delegate = AsyncMock(return_value=mock_obs)

        with pytest.raises(RuntimeError, match="max_steps"):
            await orchestrator.run("Test goal")

    @pytest.mark.asyncio
    async def test_delegate_creates_tuple_and_executes(self, orchestrator):
        """_delegate creates AgentTuple and calls factory."""
        from aorchestra.orchestrator.actions import DelegateAction

        action = DelegateAction(
            instruction="Calculate 1+1",
            context="Math task",
            tools=[],
            reasoning="Need computation",
        )

        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)

        # Mock the factory
        mock_obs = Observation(result_summary="2")
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ) as mock_execute:
            observation = await orchestrator._delegate(action)

            assert observation.result_summary == "2"
            mock_execute.assert_called_once()
            # Verify the tuple was created correctly
            call_args = mock_execute.call_args[0][0]
            assert call_args.instruction == "Calculate 1+1"
            assert call_args.context == "Math task"

    @pytest.mark.asyncio
    async def test_integrate_observation_updates_state(self, orchestrator):
        """_integrate_observation adds delegation to history."""
        from aorchestra.orchestrator.actions import DelegateAction

        action = DelegateAction(
            instruction="Test",
            reasoning="Test",
        )
        observation = Observation(result_summary="Done")

        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)

        orchestrator._integrate_observation(action, observation)

        assert len(orchestrator.state.history) == 1
        assert orchestrator.state.step == 1
        assert orchestrator.state.history[0].observation.result_summary == "Done"

    @pytest.mark.asyncio
    async def test_orchestrator_uses_custom_factory(self, model_config):
        """Orchestrator uses the provided factory for delegation."""
        from aorchestra.core.factory import AgentFactory

        # Create a mock factory
        custom_factory = AgentFactory()
        mock_obs = Observation(result_summary="Custom factory result")

        with patch.object(
            custom_factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ) as mock_execute:
            orch = Orchestrator(model=model_config, factory=custom_factory, max_steps=5)

            # Initialize state and test delegation
            from aorchestra.orchestrator.state import OrchestratorState
            from aorchestra.orchestrator.actions import DelegateAction
            orch.state = OrchestratorState(goal="Test", max_steps=5)

            action = DelegateAction(instruction="Test", reasoning="Test")
            await orch._delegate(action)

            # Verify custom factory was called
            mock_execute.assert_called_once()
