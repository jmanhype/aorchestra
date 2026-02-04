"""Tests for OrchestratorState and Delegation models."""

from aorchestra.orchestrator.state import Delegation, OrchestratorState
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord


class TestDelegation:
    """Tests for Delegation model."""

    def test_delegation_with_cost_record(self):
        """Test Delegation includes cost_record field."""
        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])
        cost_record = CostRecord(
            model_name="test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )

        delegation = Delegation(
            step=1,
            tuple=tuple_def,
            observation=observation,
            cost_record=cost_record,
        )

        assert delegation.step == 1
        assert delegation.tuple == tuple_def
        assert delegation.observation == observation
        assert delegation.cost_record == cost_record
        assert delegation.timestamp  # Should have timestamp

    def test_delegation_serialization(self):
        """Test Delegation can be serialized to/from JSON."""
        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])
        cost_record = CostRecord(
            model_name="test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )

        delegation = Delegation(
            step=1,
            tuple=tuple_def,
            observation=observation,
            cost_record=cost_record,
        )

        json_str = delegation.model_dump_json()
        assert "cost_record" in json_str

        delegation2 = Delegation.model_validate_json(json_str)
        assert delegation2.cost_record.total_tokens == 150


class TestOrchestratorState:
    """Tests for OrchestratorState model."""

    def test_total_cost_usd_field(self):
        """Test OrchestratorState has total_cost_usd field."""
        state = OrchestratorState(goal="Test goal")
        assert hasattr(state, "total_cost_usd")
        assert state.total_cost_usd == 0.0

    def test_total_cost_usd_default(self):
        """Test total_cost_usd defaults to 0.0."""
        state = OrchestratorState(goal="Test goal")
        assert state.total_cost_usd == 0.0

    def test_add_delegation_increments_cost(self):
        """Test add_delegation() increments total_cost_usd."""
        state = OrchestratorState(goal="Test goal")

        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])
        cost_record = CostRecord(
            model_name="test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )

        delegation = Delegation(
            step=1,
            tuple=tuple_def,
            observation=observation,
            cost_record=cost_record,
        )

        state.add_delegation(delegation)

        assert state.total_cost_usd == 0.0015
        assert state.step == 1

    def test_add_delegation_accumulates_costs(self):
        """Test add_delegation() accumulates costs across multiple delegations."""
        state = OrchestratorState(goal="Test goal")

        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])

        # Add three delegations with different costs
        for i, cost in enumerate([0.001, 0.002, 0.003]):
            cost_record = CostRecord(
                model_name="test",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=cost,
            )
            delegation = Delegation(
                step=i + 1,
                tuple=tuple_def,
                observation=observation,
                cost_record=cost_record,
            )
            state.add_delegation(delegation)

        assert state.total_cost_usd == 0.006
        assert state.step == 3

    def test_get_cost_summary(self):
        """Test get_cost_summary() returns correct breakdown."""
        state = OrchestratorState(goal="Test goal")

        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])

        # Add delegations with different models
        cost_record1 = CostRecord(
            model_name="glm-4-flash",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.001,
        )
        delegation1 = Delegation(
            step=1, tuple=tuple_def, observation=observation, cost_record=cost_record1
        )

        cost_record2 = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            estimated_cost_usd=0.005,
        )
        delegation2 = Delegation(
            step=2, tuple=tuple_def, observation=observation, cost_record=cost_record2
        )

        state.add_delegation(delegation1)
        state.add_delegation(delegation2)

        summary = state.get_cost_summary()

        assert summary["total_cost_usd"] == 0.006
        assert summary["total_tokens"] == 450
        assert summary["delegation_count"] == 2
        assert "model_breakdown" in summary

        # Check model breakdown
        assert "glm-4-flash" in summary["model_breakdown"]
        assert summary["model_breakdown"]["glm-4-flash"]["cost_usd"] == 0.001
        assert summary["model_breakdown"]["glm-4-flash"]["tokens"] == 150
        assert summary["model_breakdown"]["glm-4-flash"]["calls"] == 1

        assert "glm-4.7" in summary["model_breakdown"]
        assert summary["model_breakdown"]["glm-4.7"]["cost_usd"] == 0.005
        assert summary["model_breakdown"]["glm-4.7"]["tokens"] == 300
        assert summary["model_breakdown"]["glm-4.7"]["calls"] == 1

    def test_get_cost_summary_empty(self):
        """Test get_cost_summary() returns correct values for empty state."""
        state = OrchestratorState(goal="Test goal")

        summary = state.get_cost_summary()

        assert summary["total_cost_usd"] == 0.0
        assert summary["total_tokens"] == 0
        assert summary["delegation_count"] == 0
        assert summary["model_breakdown"] == {}

    def test_cost_breakdown_aggregates_same_model(self):
        """Test model_breakdown aggregates correctly for same model."""
        state = OrchestratorState(goal="Test goal")

        config = ModelConfig(name="test", api_base="https://example.com")
        tuple_def = AgentTuple(instruction="Test", model=config)
        observation = Observation(result_summary="Success", artifacts={}, error_logs=[])

        # Add multiple delegations with same model
        for i in range(3):
            cost_record = CostRecord(
                model_name="glm-4.7",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.001,
            )
            delegation = Delegation(
                step=i + 1,
                tuple=tuple_def,
                observation=observation,
                cost_record=cost_record,
            )
            state.add_delegation(delegation)

        summary = state.get_cost_summary()
        breakdown = summary["model_breakdown"]["glm-4.7"]

        assert breakdown["calls"] == 3
        assert breakdown["tokens"] == 450
        assert breakdown["cost_usd"] == 0.003
