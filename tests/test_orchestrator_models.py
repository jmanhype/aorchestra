"""Tests for orchestrator state and action models."""

import pytest

from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig


class TestOrchestratorState:
    """Test OrchestratorState model."""

    def test_create_state(self):
        """Create a valid OrchestratorState."""
        state = OrchestratorState(goal="Test goal")
        assert state.goal == "Test goal"
        assert state.step == 0
        assert state.history == []
        assert state.max_steps == 20
        assert state.is_finished is False

    def test_max_steps_custom(self):
        """Custom max_steps constraint."""
        state = OrchestratorState(goal="Test", max_steps=5)
        assert state.max_steps == 5

    def test_is_finished_when_step_equals_max(self):
        """is_finished returns True when step == max_steps."""
        state = OrchestratorState(goal="Test", max_steps=2, step=2)
        assert state.is_finished is True

    def test_is_finished_when_step_exceeds_max(self):
        """is_finished returns True when step > max_steps."""
        state = OrchestratorState(goal="Test", max_steps=2, step=3)
        assert state.is_finished is True

    def test_add_delegation_increments_step(self):
        """add_delegation adds to history and increments step."""
        state = OrchestratorState(goal="Test")
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Test",
                model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
            ),
            observation=Observation(result_summary="Done"),
        )
        state.add_delegation(delegation)
        assert state.step == 1
        assert len(state.history) == 1

    def test_state_serialization(self):
        """OrchestratorState can be serialized to JSON."""
        state = OrchestratorState(
            goal="Test goal",
            max_steps=10,
        )
        json_str = state.model_dump_json()
        assert "goal" in json_str
        assert "max_steps" in json_str


class TestDelegateAction:
    """Test DelegateAction model."""

    def test_create_delegate_action(self):
        """Create a valid DelegateAction."""
        action = DelegateAction(
            instruction="Calculate something",
            reasoning="Need computation",
        )
        assert action.instruction == "Calculate something"
        assert action.context == ""
        assert action.tools == []
        assert action.reasoning == "Need computation"

    def test_delegate_action_with_all_fields(self):
        """Create DelegateAction with all fields."""
        action = DelegateAction(
            instruction="Search web",
            context="User query: X",
            tools=["search", "calculator"],
            reasoning="Need external data",
        )
        assert len(action.tools) == 2
        assert action.context == "User query: X"

    def test_delegate_action_serialization(self):
        """DelegateAction can be serialized to JSON."""
        action = DelegateAction(
            instruction="Test",
            reasoning="Test",
        )
        json_str = action.model_dump_json()
        assert "instruction" in json_str
        assert "reasoning" in json_str


class TestFinishAction:
    """Test FinishAction model."""

    def test_create_finish_action(self):
        """Create a valid FinishAction."""
        action = FinishAction(
            answer="The answer is 42",
            reasoning="Calculation complete",
        )
        assert action.answer == "The answer is 42"
        assert action.reasoning == "Calculation complete"

    def test_finish_action_serialization(self):
        """FinishAction can be serialized to JSON."""
        action = FinishAction(
            answer="Done",
            reasoning="Complete",
        )
        json_str = action.model_dump_json()
        assert "answer" in json_str
        assert "reasoning" in json_str


class TestDelegation:
    """Test Delegation model."""

    @pytest.fixture
    def sample_tuple(self):
        """Sample AgentTuple."""
        return AgentTuple(
            instruction="Test task",
            model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
        )

    @pytest.fixture
    def sample_observation(self):
        """Sample Observation."""
        return Observation(result_summary="Task completed")

    def test_create_delegation(self, sample_tuple, sample_observation):
        """Create a valid Delegation."""
        delegation = Delegation(
            step=0,
            tuple=sample_tuple,
            observation=sample_observation,
        )
        assert delegation.step == 0
        assert delegation.tuple == sample_tuple
        assert delegation.observation == sample_observation
        assert delegation.timestamp  # Non-empty timestamp

    def test_delegation_serialization(self, sample_tuple, sample_observation):
        """Delegation can be serialized to JSON."""
        delegation = Delegation(
            step=0,
            tuple=sample_tuple,
            observation=sample_observation,
        )
        json_str = delegation.model_dump_json()
        assert "step" in json_str
        assert "timestamp" in json_str

    def test_delegation_with_error_logs(self, sample_tuple):
        """Delegation can contain error logs from observation."""
        obs = Observation(
            result_summary="Partial success",
            error_logs=["Warning: API timeout"],
        )
        delegation = Delegation(
            step=0,
            tuple=sample_tuple,
            observation=obs,
        )
        assert len(delegation.observation.error_logs) == 1
        assert "API timeout" in delegation.observation.error_logs[0]
