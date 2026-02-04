"""Tests for Orchestrator class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import FinishAction
from aorchestra.models.cost import CostRecord


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
        # Item 004: Check for ModelRegistry and CostTracker
        assert orch.model_registry is not None
        assert orch.cost_tracker is not None
        assert orch.lambda_param == 0.5

    def test_initialization_with_custom_factory(self, model_config):
        """Orchestrator can accept a custom factory."""
        from aorchestra.core.factory import AgentFactory
        custom_factory = AgentFactory()
        orch = Orchestrator(model=model_config, factory=custom_factory)
        assert orch.factory == custom_factory

    def test_initialization_with_custom_lambda(self, model_config):
        """Orchestrator can accept custom lambda parameter."""
        orch = Orchestrator(model=model_config, lambda_param=0.9)
        assert orch.lambda_param == 0.9

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

        # Mock _delegate to return observation and cost record (Item 004)
        mock_obs = Observation(result_summary="Done")
        mock_cost = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.001,
        )
        orchestrator._delegate = AsyncMock(return_value=(mock_obs, mock_cost))

        with pytest.raises(RuntimeError, match="max_steps"):
            await orchestrator.run("Test goal")

    @pytest.mark.asyncio
    async def test_delegate_creates_tuple_and_executes(self, orchestrator):
        """_delegate creates AgentTuple and calls factory."""
        from aorchestra.orchestrator.actions import DelegateAction
        from aorchestra.models.cost import CostRecord

        action = DelegateAction(
            instruction="Calculate 1+1",
            context="Math task",
            tools=[],
            reasoning="Need computation",
        )

        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)

        # Mock factory to return observation and cost record (Item 004)
        mock_obs = Observation(result_summary="2")
        mock_cost = CostRecord(
            model_name="glm-4-flash",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60,
            estimated_cost_usd=0.00002,
        )
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=(mock_obs, mock_cost))
        ) as mock_execute:
            observation, cost_record = await orchestrator._delegate(action)

            assert observation.result_summary == "2"
            assert cost_record.total_tokens == 60
            mock_execute.assert_called_once()
            # Verify tuple was created correctly
            call_args = mock_execute.call_args[0][0]
            assert call_args.instruction == "Calculate 1+1"
            assert call_args.context == "Math task"

    @pytest.mark.asyncio
    async def test_integrate_observation_updates_state(self, orchestrator):
        """_integrate_observation adds delegation to history."""
        from aorchestra.orchestrator.actions import DelegateAction
        from aorchestra.models.cost import CostRecord

        action = DelegateAction(
            instruction="Test",
            reasoning="Test",
        )
        observation = Observation(result_summary="Done")
        cost_record = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.001,
        )

        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)

        orchestrator._integrate_observation(action, observation, cost_record)

        assert len(orchestrator.state.history) == 1
        assert orchestrator.state.step == 1
        assert orchestrator.state.history[0].observation.result_summary == "Done"
        assert orchestrator.state.total_cost_usd == 0.001
        assert orchestrator.state.history[0].cost_record.total_tokens == 150

    @pytest.mark.asyncio
    async def test_orchestrator_uses_custom_factory(self, model_config):
        """Orchestrator uses the provided factory for delegation."""
        from aorchestra.core.factory import AgentFactory

        # Create a mock factory
        custom_factory = AgentFactory()
        mock_obs = Observation(result_summary="Custom factory result")
        mock_cost = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.001,
        )

        with patch.object(
            custom_factory, "create_and_execute", new=AsyncMock(return_value=(mock_obs, mock_cost))
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
