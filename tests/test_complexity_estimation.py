"""Tests for complexity estimation and model selection."""

import pytest

from aorchestra.orchestrator.selection import (
    COMPLEXITY_KEYWORDS,
    COMPLEX_TOOLS,
    estimate_complexity,
    select_model_by_criteria,
)


class TestEstimateComplexity:
    """Tests for estimate_complexity function."""

    def test_empty_instruction(self):
        """Test empty instruction returns 0.0."""
        score = estimate_complexity("", [], 0)
        assert score == 0.0

    def test_empty_tools(self):
        """Test empty tools works correctly."""
        score = estimate_complexity("Simple task", [], 100)
        assert score >= 0.0
        assert score < 0.5

    def test_instruction_length_contribution(self):
        """Test instruction length contributes correctly (max 0.3 at 500 chars)."""
        # Short instruction
        score1 = estimate_complexity("Short", [], 0)
        assert score1 < 0.1

        # 500 chars should get max 0.3 from length
        instruction_500 = "a" * 500
        score2 = estimate_complexity(instruction_500, [], 0)
        length_contribution = score2  # No other factors
        assert length_contribution == pytest.approx(0.3, abs=0.01)

        # Longer than 500 chars should still max at 0.3
        instruction_1000 = "a" * 1000
        score3 = estimate_complexity(instruction_1000, [], 0)
        assert score3 == pytest.approx(score2, abs=0.01)

    def test_keywords_contribution(self):
        """Test keywords contribute correctly."""
        # No keywords
        score1 = estimate_complexity("Add two numbers", [], 0)
        assert score1 < 0.1

        # One keyword
        score2 = estimate_complexity("Analyze this", [], 0)
        assert score2 > score1

        # Multiple keywords (should cap at 0.3)
        instruction = "Analyze optimize design complex algorithm"
        score3 = estimate_complexity(instruction, [], 0)
        assert score3 >= 0.0
        assert score3 <= 1.0
        assert score3 > score2  # Multiple keywords should increase score

    def test_keyword_case_insensitive(self):
        """Test keyword matching is case-insensitive."""
        score1 = estimate_complexity("ANALYZE this", [], 0)
        score2 = estimate_complexity("analyze this", [], 0)
        score3 = estimate_complexity("Analyze This", [], 0)

        assert score1 == pytest.approx(score2)
        assert score2 == pytest.approx(score3)

    def test_tools_contribution(self):
        """Test complex tools contribute correctly."""
        # No tools
        score1 = estimate_complexity("Task", [], 0)
        assert score1 < 0.1

        # Simple tool (not in COMPLEX_TOOLS)
        score2 = estimate_complexity("Task", ["simple_tool"], 0)
        assert score2 == pytest.approx(score1)

        # Complex tool
        score3 = estimate_complexity("Task", ["code_execute"], 0)
        assert score3 > score2

        # Multiple complex tools (should cap at 0.3)
        score4 = estimate_complexity("Task", ["code_execute", "web_search"], 0)
        assert score4 >= 0.0
        assert score4 <= 1.0

    def test_context_size_contribution(self):
        """Test context size contributes correctly (max 0.1 at 2000 chars)."""
        # No context
        score1 = estimate_complexity("Task", [], 0)
        context_only = score1  # Assuming instruction is simple

        # 2000 chars should get max 0.1 from context
        score2 = estimate_complexity("Task", [], 2000)
        context_contribution = score2 - context_only
        assert context_contribution == pytest.approx(0.1, abs=0.01)

        # Larger context should still max at 0.1
        score3 = estimate_complexity("Task", [], 4000)
        assert score3 == pytest.approx(score2, abs=0.01)

    def test_score_capped_at_1_0(self):
        """Test score is capped at 1.0."""
        # Very long instruction with all keywords, all tools, large context
        instruction = "Analyze optimize design complex algorithm architecture planning " * 10
        tools = list(COMPLEX_TOOLS.keys())
        score = estimate_complexity(instruction, tools, 10000)

        assert score == pytest.approx(1.0, abs=0.01)

    def test_simple_task_low_score(self):
        """Test simple task returns low score (< 0.4)."""
        score = estimate_complexity("Add 2 + 2", [], 50)
        assert score < 0.4

    def test_complex_task_high_score(self):
        """Test complex task returns high score (> 0.6)."""
        instruction = "Analyze and optimize the recursive algorithm for performance, design new architecture"
        tools = ["code_execute", "web_search"]
        score = estimate_complexity(instruction, tools, 1500)
        assert score > 0.6

    def test_all_factors_combined(self):
        """Test all factors combine correctly."""
        # Simple instruction with no keywords (100 chars -> 0.2)
        instruction = "x" * 100
        # One complex tool (+0.3 for code_execute)
        tools = ["code_execute"]
        # Medium context (1000 chars -> 0.05)
        context_length = 1000

        score = estimate_complexity(instruction, tools, context_length)
        # All factors should contribute
        assert 0.5 <= score <= 1.0  # Reasonable range for this combination
        assert score > 0.0  # Score should be positive

    def test_specific_keywords(self):
        """Test specific keywords from COMPLEXITY_KEYWORDS."""
        # Test a few specific keywords
        test_cases = [
            ("optimize this", "optimize"),
            ("design system", "design"),
            ("debug the code", "debug"),
            ("implement feature", "implement"),
            ("security check", "security"),
        ]

        for instruction, keyword in test_cases:
            score = estimate_complexity(instruction, [], 0)
            assert score > 0.0, f"Keyword '{keyword}' should contribute to score"

    def test_specific_tools(self):
        """Test specific tools from COMPLEX_TOOLS."""
        # Test a few specific tools
        test_tools = ["code_execute", "web_search", "file_read"]

        for tool in test_tools:
            score = estimate_complexity("Task", [tool], 0)
            assert score > 0.0, f"Tool '{tool}' should contribute to score"


class TestSelectModelByCriteria:
    """Tests for select_model_by_criteria function."""

    def test_select_model_delegates_to_registry(self):
        """Test select_model_by_criteria delegates to ModelRegistry."""
        from aorchestra.models.config import ModelConfig
        from aorchestra.models.cost import ModelSelectionCriteria, ModelTier
        from aorchestra.models.registry import ModelRegistry

        registry = ModelRegistry()
        config = ModelConfig(
            name="test-model", api_base="https://example.com", api_key="key"
        )
        tier = ModelTier(
            name="test-model",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )
        registry.register(config, tier)

        criteria = ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)
        model = select_model_by_criteria(criteria, registry)

        assert model.name == "test-model"

    def test_select_model_raises_error_on_empty_registry(self):
        """Test select_model_by_criteria raises ValueError on empty registry."""
        from aorchestra.models.cost import ModelSelectionCriteria
        from aorchestra.models.registry import ModelRegistry

        registry = ModelRegistry()
        criteria = ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)

        with pytest.raises(ValueError, match="No models registered"):
            select_model_by_criteria(criteria, registry)

    def test_select_model_with_tier_preference(self):
        """Test select_model_by_criteria respects tier_preference."""
        from aorchestra.models.config import ModelConfig
        from aorchestra.models.cost import ModelSelectionCriteria, ModelTier
        from aorchestra.models.registry import ModelRegistry

        registry = ModelRegistry()
        for tier_name in ["flash", "standard", "premium"]:
            config = ModelConfig(
                name=f"{tier_name}-model", api_base="https://example.com", api_key="key"
            )
            tier = ModelTier(
                name=f"{tier_name}-model",
                tier=tier_name,
                description=f"{tier_name}",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            )
            registry.register(config, tier)

        criteria = ModelSelectionCriteria(
            complexity=0.5, lambda_param=0.5, tier_preference="flash"
        )
        model = select_model_by_criteria(criteria, registry)

        assert model.name == "flash-model"
