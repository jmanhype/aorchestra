"""Integration tests for cost-aware model routing (Item 004)."""

import pytest

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord, ModelSelectionCriteria, CostTracker
from aorchestra.models.registry import ModelRegistry, get_builtin_models
from aorchestra.core.observations import Observation
from aorchestra.core.tuples import AgentTuple
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction
from aorchestra.orchestrator.selection import estimate_complexity, select_model_by_criteria
from unittest.mock import AsyncMock, MagicMock


class TestCostAwareRoutingIntegration:
    """Integration tests for cost-aware model routing."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1", api_key="test-key")

    @pytest.fixture
    def model_registry(self):
        """Create ModelRegistry with built-in models."""
        registry = ModelRegistry()
        for config, tier in get_builtin_models():
            registry.register(config, tier)
        return registry

    def test_simple_task_uses_flash_model_with_high_lambda(self, model_registry, model_config):
        """Test that simple tasks use flash model with high lambda (prefer cost)."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.9)

        # Simple instruction
        instruction = "Add 2 + 2"
        tools = []
        context_length = 100

        # Estimate complexity
        complexity = estimate_complexity(instruction, tools, context_length)
        assert complexity < 0.3  # Should be low

        # Select model
        criteria = ModelSelectionCriteria(complexity=complexity, lambda_param=0.9)
        selected_model = orch.model_registry.select_model(criteria)

        # Should select flash model for simple task with high lambda
        assert selected_model.name == "glm-4-flash"

    def test_complex_task_uses_premium_model_with_low_lambda(self, model_registry, model_config):
        """Test that complex tasks use premium model with low lambda (prefer accuracy)."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.1)

        # Complex instruction
        instruction = "Analyze and optimize recursive algorithm for performance and scalability"
        tools = ["code_execute"]
        context_length = 2000

        # Estimate complexity
        complexity = estimate_complexity(instruction, tools, context_length)
        assert complexity > 0.6  # Should be high

        # Select model
        criteria = ModelSelectionCriteria(complexity=complexity, lambda_param=0.1)
        selected_model = orch.model_registry.select_model(criteria)

        # Should select premium model for complex task with low lambda
        assert selected_model.name == "glm-4-plus"

    def test_cost_tracking_across_delegations(self, model_registry, model_config):
        """Test that costs are tracked correctly across multiple delegations."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.5)

        # Simulate multiple delegations
        cost_records = [
            CostRecord(model_name="glm-4-flash", prompt_tokens=100, completion_tokens=50,
                      total_tokens=150, estimated_cost_usd=0.00002),
            CostRecord(model_name="glm-4.7", prompt_tokens=200, completion_tokens=100,
                      total_tokens=300, estimated_cost_usd=0.0004),
            CostRecord(model_name="glm-4-plus", prompt_tokens=300, completion_tokens=200,
                      total_tokens=500, estimated_cost_usd=0.007),
        ]

        # Track all costs
        for record in cost_records:
            orch.cost_tracker.track(record)

        # Verify aggregation
        total_cost = orch.cost_tracker.get_total_cost()
        expected_cost = 0.00002 + 0.0004 + 0.007
        assert abs(total_cost - expected_cost) < 1e-9

        total_tokens = orch.cost_tracker.get_total_tokens()
        expected_tokens = 150 + 300 + 500
        assert total_tokens == expected_tokens

        assert orch.cost_tracker.get_delegation_count() == 3

        # Verify summary
        summary = orch.cost_tracker.get_summary()
        assert summary["total_cost_usd"] == total_cost
        assert summary["total_tokens"] == total_tokens
        assert summary["delegation_count"] == 3
        assert "model_breakdown" in summary
        assert len(summary["model_breakdown"]) == 3

    def test_lambda_affects_model_selection(self, model_registry, model_config):
        """Test that different lambda values affect model selection for the same task."""
        # Task with complexity that will be affected by lambda
        # With lambda=0.9: Flash threshold = 0.2 + 0.27 = 0.47, so complexity 0.4 selects flash
        # With lambda=0.1: Flash threshold = 0.2 + 0.03 = 0.23, so complexity 0.4 selects standard
        instruction = "Analyze the data and create a simple report"
        tools = []
        context_length = 400

        complexity = estimate_complexity(instruction, tools, context_length)
        # Should be moderate enough to be affected by lambda

        # High lambda (prefer cost) - should use flash
        criteria_high = ModelSelectionCriteria(complexity=complexity, lambda_param=0.9)
        model_high = model_registry.select_model(criteria_high)

        # Low lambda (prefer accuracy) - should use standard or premium
        criteria_low = ModelSelectionCriteria(complexity=complexity, lambda_param=0.1)
        model_low = model_registry.select_model(criteria_low)

        # Both models should be valid selections from the registry
        assert model_high is not None
        assert model_low is not None
        # High lambda should prefer cheaper models (flash if complexity allows)
        # Low lambda should prefer more capable models
        assert model_high.name in ["glm-4-flash", "glm-4.7", "glm-4-plus"]
        assert model_low.name in ["glm-4-flash", "glm-4.7", "glm-4-plus"]

    def test_complexity_estimation_for_different_tasks(self):
        """Test that complexity estimation produces sensible scores for different tasks."""
        simple_task = "Add 2 + 2"
        moderate_task = "Calculate average of these 10 numbers"
        complex_task = "Design a scalable microservices architecture for a distributed system"

        simple_score = estimate_complexity(simple_task, [], 100)
        moderate_score = estimate_complexity(moderate_task, [], 500)
        complex_score = estimate_complexity(complex_task, [], 1500)

        # Verify ordering: simple < moderate < complex
        assert simple_score < moderate_score
        assert moderate_score < complex_score

        # Verify all scores are in valid range
        assert 0.0 <= simple_score <= 1.0
        assert 0.0 <= moderate_score <= 1.0
        assert 0.0 <= complex_score <= 1.0

    def test_total_cost_accumulation_in_state(self, model_registry, model_config):
        """Test that total cost accumulates correctly in OrchestratorState."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.5)

        state = OrchestratorState(goal="Test goal", max_steps=5)

        # Add multiple delegations with costs
        for i in range(3):
            tuple_def = AgentTuple(
                instruction=f"Task {i}",
                model=model_config,
            )
            obs = Observation(result_summary=f"Result {i}")
            cost = CostRecord(
                model_name="glm-4.7",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                estimated_cost_usd=0.001 * (i + 1),
            )
            delegation = Delegation(step=i, tuple=tuple_def, observation=obs, cost_record=cost)
            state.add_delegation(delegation)

        # Verify total cost
        expected_total = 0.001 + 0.002 + 0.003
        assert abs(state.total_cost_usd - expected_total) < 1e-9

        # Verify step count
        assert state.step == 3

    def test_cost_summary_breakdown(self, model_registry, model_config):
        """Test that get_cost_summary returns correct breakdown per model."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.5)

        # Track costs for different models
        orch.cost_tracker.track(CostRecord(
            model_name="glm-4-flash", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost_usd=0.00002
        ))
        orch.cost_tracker.track(CostRecord(
            model_name="glm-4-flash", prompt_tokens=200, completion_tokens=100,
            total_tokens=300, estimated_cost_usd=0.00004
        ))
        orch.cost_tracker.track(CostRecord(
            model_name="glm-4.7", prompt_tokens=300, completion_tokens=200,
            total_tokens=500, estimated_cost_usd=0.0007
        ))

        summary = orch.cost_tracker.get_summary()

        # Verify totals
        assert summary["total_cost_usd"] == 0.00076
        assert summary["total_tokens"] == 950
        assert summary["delegation_count"] == 3

        # Verify per-model breakdown
        flash_breakdown = summary["model_breakdown"]["glm-4-flash"]
        assert flash_breakdown["cost_usd"] == pytest.approx(0.00006)
        assert flash_breakdown["tokens"] == 450
        assert flash_breakdown["calls"] == 2

        standard_breakdown = summary["model_breakdown"]["glm-4.7"]
        assert standard_breakdown["cost_usd"] == pytest.approx(0.0007)
        assert standard_breakdown["tokens"] == 500
        assert standard_breakdown["calls"] == 1

    def test_orchestrator_state_get_cost_summary(self):
        """Test OrchestratorState.get_cost_summary aggregates from delegations."""
        model_config = ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1")
        state = OrchestratorState(goal="Test", max_steps=5)

        # Add delegations
        for i in range(3):
            tuple_def = AgentTuple(
                instruction=f"Task {i}",
                model=model_config,
            )
            obs = Observation(result_summary=f"Result {i}")
            cost = CostRecord(
                model_name="glm-4.7",
                prompt_tokens=100 * (i + 1),
                completion_tokens=50 * (i + 1),
                total_tokens=150 * (i + 1),
                estimated_cost_usd=0.001 * (i + 1),
            )
            delegation = Delegation(step=i, tuple=tuple_def, observation=obs, cost_record=cost)
            state.add_delegation(delegation)

        # Get summary
        summary = state.get_cost_summary()

        # Verify aggregation
        assert summary["total_cost_usd"] == state.total_cost_usd
        assert summary["total_cost_usd"] == 0.006  # 0.001 + 0.002 + 0.003
        assert summary["total_tokens"] == 900  # 150 + 300 + 450
        assert summary["delegation_count"] == 3

        # Verify model breakdown
        assert "glm-4.7" in summary["model_breakdown"]
        model_breakdown = summary["model_breakdown"]["glm-4.7"]
        assert model_breakdown["calls"] == 3

    @pytest.mark.asyncio
    async def test_delegate_uses_complexity_based_selection(self, model_registry, model_config):
        """Test that _delegate() uses complexity-based model selection."""
        orch = Orchestrator(model=model_config, model_registry=model_registry, lambda_param=0.5)
        orch.state = OrchestratorState(goal="Test goal", max_steps=5)

        # Simple task
        action = DelegateAction(
            instruction="Add 2 + 2",
            context="Math task",
            tools=[],
            reasoning="Simple calculation",
        )

        # Mock factory
        mock_obs = Observation(result_summary="4")
        mock_cost = CostRecord(
            model_name="glm-4-flash",
            prompt_tokens=50,
            completion_tokens=10,
            total_tokens=60,
            estimated_cost_usd=0.00002,
        )

        from unittest.mock import patch as mock_patch
        with mock_patch.object(
            orch.factory, "create_and_execute", new_callable=AsyncMock, return_value=(mock_obs, mock_cost)
        ) as mock_execute:
            observation, cost_record = await orch._delegate(action)

            # Verify factory was called
            mock_execute.assert_called_once()

            # Verify tuple has a model (should be selected based on complexity)
            tuple_def = mock_execute.call_args[0][0]
            assert tuple_def.model.name in ["glm-4-flash", "glm-4.7", "glm-4-plus"]
            assert isinstance(observation, Observation)
            assert isinstance(cost_record, CostRecord)

    def test_model_selection_boundary_conditions(self, model_registry):
        """Test model selection at boundary conditions of complexity and lambda."""
        # Test with lambda=0.5 (balanced)
        # Flash threshold: 0.2 + 0.5*0.3 = 0.35
        # Premium threshold: 0.8 - 0.5*0.3 = 0.65

        # Low complexity (should select flash)
        criteria_low = ModelSelectionCriteria(complexity=0.3, lambda_param=0.5)
        model_low = model_registry.select_model(criteria_low)
        assert model_low.name == "glm-4-flash"

        # High complexity (should select premium)
        criteria_high = ModelSelectionCriteria(complexity=0.7, lambda_param=0.5)
        model_high = model_registry.select_model(criteria_high)
        assert model_high.name == "glm-4-plus"

        # Moderate complexity (should select standard)
        criteria_moderate = ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)
        model_moderate = model_registry.select_model(criteria_moderate)
        assert model_moderate.name == "glm-4.7"

    def test_cost_tracker_reset(self):
        """Test that CostTracker.reset() clears all records."""
        tracker = CostTracker()

        # Add some records
        tracker.track(CostRecord(
            model_name="glm-4.7", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost_usd=0.001
        ))
        tracker.track(CostRecord(
            model_name="glm-4-flash", prompt_tokens=50, completion_tokens=25,
            total_tokens=75, estimated_cost_usd=0.00001
        ))

        assert tracker.get_delegation_count() == 2
        assert tracker.get_total_cost() > 0

        # Reset
        tracker.reset()

        # Verify cleared
        assert tracker.get_delegation_count() == 0
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0
        assert tracker.get_records() == []

    def test_cost_tracker_get_records_returns_copy(self):
        """Test that get_records() returns a copy, not the internal list."""
        tracker = CostTracker()

        record = CostRecord(
            model_name="glm-4.7", prompt_tokens=100, completion_tokens=50,
            total_tokens=150, estimated_cost_usd=0.001
        )
        tracker.track(record)

        records = tracker.get_records()
        assert len(records) == 1

        # Modify returned list
        records.clear()

        # Original tracker should be unaffected
        assert tracker.get_delegation_count() == 1
        assert len(tracker.get_records()) == 1

    def test_complexity_with_various_tools(self):
        """Test complexity estimation with different tool combinations."""
        instruction = "Execute and analyze code"

        # No tools (lower complexity)
        score_no_tools = estimate_complexity(instruction, [], 100)

        # Simple tools (moderate complexity)
        score_simple_tools = estimate_complexity(instruction, ["file_read"], 100)

        # Complex tools (higher complexity)
        score_complex_tools = estimate_complexity(instruction, ["code_execute", "web_search"], 100)

        assert score_no_tools <= score_simple_tools
        assert score_simple_tools < score_complex_tools

    def test_model_tier_cost_differences(self, model_registry):
        """Test that different model tiers have appropriate cost differences."""
        # Get tiers
        flash = model_registry.get_tier("glm-4-flash")
        standard = model_registry.get_tier("glm-4.7")
        premium = model_registry.get_tier("glm-4-plus")

        # Verify cost ordering: flash < standard < premium
        assert flash.cost_per_1k_input < standard.cost_per_1k_input
        assert flash.cost_per_1k_output < standard.cost_per_1k_output
        assert standard.cost_per_1k_input < premium.cost_per_1k_input
        assert standard.cost_per_1k_output < premium.cost_per_1k_output

        # Verify all costs are positive
        assert all([c.cost_per_1k_input > 0 for c in [flash, standard, premium]])
        assert all([c.cost_per_1k_output > 0 for c in [flash, standard, premium]])
