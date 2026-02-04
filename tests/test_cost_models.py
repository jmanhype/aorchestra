"""Tests for cost tracking models (CostRecord, ModelTier, ModelSelectionCriteria)."""

import pytest
from pydantic import ValidationError

from aorchestra.models.cost import CostRecord, ModelTier, ModelSelectionCriteria


class TestCostRecord:
    """Tests for CostRecord model."""

    def test_create_cost_record(self):
        """Test creating a CostRecord with all fields."""
        record = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )
        assert record.model_name == "glm-4.7"
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.total_tokens == 150
        assert record.estimated_cost_usd == 0.0015
        assert record.timestamp  # Should have a timestamp

    def test_cost_record_validation(self):
        """Test CostRecord validates field constraints."""
        # Valid: all zeros
        CostRecord(
            model_name="test",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
        )

        # Invalid: negative tokens
        with pytest.raises(ValidationError):
            CostRecord(
                model_name="test",
                prompt_tokens=-1,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
            )

        # Invalid: negative cost
        with pytest.raises(ValidationError):
            CostRecord(
                model_name="test",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=-0.01,
            )

    def test_from_openai_usage(self):
        """Test creating CostRecord from OpenAI usage object."""
        # Create mock usage object
        class MockUsage:
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150

        usage = MockUsage()
        record = CostRecord.from_openai_usage(
            model_name="glm-4.7",
            usage=usage,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        assert record.model_name == "glm-4.7"
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.total_tokens == 150
        assert record.estimated_cost_usd == pytest.approx(0.0002)  # (100/1000)*0.001 + (50/1000)*0.002

    def test_from_openai_usage_no_rates(self):
        """Test CostRecord.from_openai_usage with zero rates."""
        class MockUsage:
            prompt_tokens = 100
            completion_tokens = 50
            total_tokens = 150

        usage = MockUsage()
        record = CostRecord.from_openai_usage(model_name="glm-4.7", usage=usage)

        assert record.estimated_cost_usd == 0.0

    def test_from_openai_usage_none(self):
        """Test CostRecord.from_openai_usage with None usage."""
        record = CostRecord.from_openai_usage(model_name="glm-4.7", usage=None)

        assert record.prompt_tokens == 0
        assert record.completion_tokens == 0
        assert record.total_tokens == 0
        assert record.estimated_cost_usd == 0.0

    def test_cost_record_serialization(self):
        """Test CostRecord can be serialized to/from JSON."""
        record = CostRecord(
            model_name="glm-4.7",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0015,
        )
        json_str = record.model_dump_json()
        assert "glm-4.7" in json_str
        assert "150" in json_str

        # Deserialize
        record2 = CostRecord.model_validate_json(json_str)
        assert record2.model_name == record.model_name
        assert record2.total_tokens == record.total_tokens


class TestModelTier:
    """Tests for ModelTier model."""

    def test_create_model_tier(self):
        """Test creating a ModelTier with all fields."""
        tier = ModelTier(
            name="glm-4-flash",
            tier="flash",
            description="Fast and cost-effective model",
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0002,
            capabilities=["text", "simple_math"],
        )
        assert tier.name == "glm-4-flash"
        assert tier.tier == "flash"
        assert tier.cost_per_1k_input == 0.0001
        assert tier.cost_per_1k_output == 0.0002
        assert "text" in tier.capabilities

    def test_model_tier_valid_tiers(self):
        """Test ModelTier accepts valid tier values."""
        ModelTier(
            name="test",
            tier="flash",
            description="Flash",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.001,
        )

        ModelTier(
            name="test",
            tier="standard",
            description="Standard",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.001,
        )

        ModelTier(
            name="test",
            tier="premium",
            description="Premium",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.001,
        )

    def test_model_tier_invalid_tier(self):
        """Test ModelTier rejects invalid tier values."""
        with pytest.raises(ValidationError):
            ModelTier(
                name="test",
                tier="invalid",
                description="Test",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.001,
            )

    def test_model_tier_cost_validation(self):
        """Test ModelTier validates cost rates are > 0."""
        # Valid
        ModelTier(
            name="test",
            tier="flash",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.001,
        )

        # Invalid: zero cost
        with pytest.raises(ValidationError):
            ModelTier(
                name="test",
                tier="flash",
                description="Test",
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.001,
            )

        # Invalid: negative cost
        with pytest.raises(ValidationError):
            ModelTier(
                name="test",
                tier="flash",
                description="Test",
                cost_per_1k_input=-0.001,
                cost_per_1k_output=0.001,
            )

    def test_model_tier_default_capabilities(self):
        """Test ModelTier has empty capabilities list by default."""
        tier = ModelTier(
            name="test",
            tier="flash",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.001,
        )
        assert tier.capabilities == []

    def test_model_tier_serialization(self):
        """Test ModelTier can be serialized to/from JSON."""
        tier = ModelTier(
            name="glm-4-flash",
            tier="flash",
            description="Fast model",
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0002,
            capabilities=["text"],
        )
        json_str = tier.model_dump_json()
        assert "flash" in json_str

        tier2 = ModelTier.model_validate_json(json_str)
        assert tier2.name == tier.name
        assert tier2.tier == tier.tier


class TestModelSelectionCriteria:
    """Tests for ModelSelectionCriteria model."""

    def test_create_criteria(self):
        """Test creating ModelSelectionCriteria with all fields."""
        criteria = ModelSelectionCriteria(
            complexity=0.7,
            lambda_param=0.5,
            tier_preference="premium",
        )
        assert criteria.complexity == 0.7
        assert criteria.lambda_param == 0.5
        assert criteria.tier_preference == "premium"

    def test_criteria_defaults(self):
        """Test ModelSelectionCriteria has sensible defaults."""
        criteria = ModelSelectionCriteria(complexity=0.5)
        assert criteria.complexity == 0.5
        assert criteria.lambda_param == 0.5  # Default
        assert criteria.tier_preference is None  # Default

    def test_criteria_complexity_validation(self):
        """Test ModelSelectionCriteria validates complexity range."""
        # Valid: 0.0 to 1.0
        ModelSelectionCriteria(complexity=0.0)
        ModelSelectionCriteria(complexity=0.5)
        ModelSelectionCriteria(complexity=1.0)

        # Invalid: negative
        with pytest.raises(ValidationError):
            ModelSelectionCriteria(complexity=-0.1)

        # Invalid: > 1.0
        with pytest.raises(ValidationError):
            ModelSelectionCriteria(complexity=1.1)

    def test_criteria_lambda_validation(self):
        """Test ModelSelectionCriteria validates lambda_param range."""
        # Valid: 0.0 to 1.0
        ModelSelectionCriteria(complexity=0.5, lambda_param=0.0)
        ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)
        ModelSelectionCriteria(complexity=0.5, lambda_param=1.0)

        # Invalid: negative
        with pytest.raises(ValidationError):
            ModelSelectionCriteria(complexity=0.5, lambda_param=-0.1)

        # Invalid: > 1.0
        with pytest.raises(ValidationError):
            ModelSelectionCriteria(complexity=0.5, lambda_param=1.1)

    def test_criteria_tier_preference_validation(self):
        """Test ModelSelectionCriteria validates tier_preference."""
        # Valid values
        ModelSelectionCriteria(complexity=0.5, tier_preference="flash")
        ModelSelectionCriteria(complexity=0.5, tier_preference="standard")
        ModelSelectionCriteria(complexity=0.5, tier_preference="premium")
        ModelSelectionCriteria(complexity=0.5, tier_preference=None)

        # Invalid value
        with pytest.raises(ValidationError):
            ModelSelectionCriteria(complexity=0.5, tier_preference="invalid")

    def test_criteria_serialization(self):
        """Test ModelSelectionCriteria can be serialized to/from JSON."""
        criteria = ModelSelectionCriteria(
            complexity=0.7,
            lambda_param=0.5,
            tier_preference="premium",
        )
        json_str = criteria.model_dump_json()
        assert "0.7" in json_str

        criteria2 = ModelSelectionCriteria.model_validate_json(json_str)
        assert criteria2.complexity == criteria.complexity
        assert criteria2.lambda_param == criteria.lambda_param
