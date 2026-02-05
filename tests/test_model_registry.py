"""Tests for ModelRegistry and get_builtin_models function."""

import pytest

from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import ModelSelectionCriteria, ModelTier
from aorchestra.models.registry import ModelRegistry, get_builtin_models


class TestModelRegistry:
    """Tests for ModelRegistry functionality."""

    def test_init_empty(self):
        """Test ModelRegistry initializes empty."""
        registry = ModelRegistry()
        assert len(registry) == 0
        assert "test" not in registry
        assert registry.get_all() == []
        assert registry.list_models() == []

    def test_register_valid(self):
        """Test registering a model with valid config and tier."""
        registry = ModelRegistry()
        config = ModelConfig(
            name="test-model",
            api_base="https://example.com",
            api_key="key",
        )
        tier = ModelTier(
            name="test-model",
            tier="standard",
            description="Test model",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        registry.register(config, tier)

        assert len(registry) == 1
        assert "test-model" in registry
        assert registry.get("test-model") == config
        assert registry.get_tier("test-model") == tier

    def test_register_name_mismatch(self):
        """Test register raises ValueError when names don't match."""
        registry = ModelRegistry()
        config = ModelConfig(name="model-a", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="model-b",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        with pytest.raises(ValueError, match="must match"):
            registry.register(config, tier)

    def test_register_duplicate(self):
        """Test register raises ValueError for duplicate models."""
        registry = ModelRegistry()
        config = ModelConfig(name="test", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="test",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        registry.register(config, tier)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(config, tier)

    def test_unregister_valid(self):
        """Test unregister removes model and tier."""
        registry = ModelRegistry()
        config = ModelConfig(name="test", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="test",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        registry.register(config, tier)
        assert len(registry) == 1

        registry.unregister("test")
        assert len(registry) == 0
        assert "test" not in registry
        assert registry.get("test") is None
        assert registry.get_tier("test") is None

    def test_unregister_nonexistent(self):
        """Test unregister raises KeyError for nonexistent model."""
        registry = ModelRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    def test_get(self):
        """Test get returns config or None."""
        registry = ModelRegistry()
        config = ModelConfig(name="test", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="test",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        assert registry.get("test") is None

        registry.register(config, tier)
        assert registry.get("test") == config

    def test_get_tier(self):
        """Test get_tier returns tier or None."""
        registry = ModelRegistry()
        config = ModelConfig(name="test", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="test",
            tier="premium",
            description="Test",
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        )

        assert registry.get_tier("test") is None

        registry.register(config, tier)
        assert registry.get_tier("test") == tier
        assert registry.get_tier("test").tier == "premium"

    def test_get_by_tier(self):
        """Test get_by_tier returns first model at tier level."""
        registry = ModelRegistry()

        # Register multiple models at different tiers
        flash_config = ModelConfig(
            name="flash-model", api_base="https://example.com", api_key="key"
        )
        flash_tier = ModelTier(
            name="flash-model",
            tier="flash",
            description="Flash",
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0002,
        )

        standard_config = ModelConfig(
            name="standard-model", api_base="https://example.com", api_key="key"
        )
        standard_tier = ModelTier(
            name="standard-model",
            tier="standard",
            description="Standard",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )

        premium_config = ModelConfig(
            name="premium-model", api_base="https://example.com", api_key="key"
        )
        premium_tier = ModelTier(
            name="premium-model",
            tier="premium",
            description="Premium",
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.02,
        )

        registry.register(flash_config, flash_tier)
        registry.register(standard_config, standard_tier)
        registry.register(premium_config, premium_tier)

        assert registry.get_by_tier("flash") == flash_config
        assert registry.get_by_tier("standard") == standard_config
        assert registry.get_by_tier("premium") == premium_config

    def test_get_by_tier_none(self):
        """Test get_by_tier returns None when no model at tier."""
        registry = ModelRegistry()

        assert registry.get_by_tier("flash") is None
        assert registry.get_by_tier("standard") is None
        assert registry.get_by_tier("premium") is None

    def test_get_all(self):
        """Test get_all returns all configs."""
        registry = ModelRegistry()
        configs = [
            ModelConfig(name=f"model-{i}", api_base="https://example.com", api_key="key")
            for i in range(3)
        ]
        tiers = [
            ModelTier(
                name=f"model-{i}",
                tier="standard",
                description="Test",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            )
            for i in range(3)
        ]

        for config, tier in zip(configs, tiers):
            registry.register(config, tier)

        all_configs = registry.get_all()
        assert len(all_configs) == 3
        assert all(isinstance(c, ModelConfig) for c in all_configs)

    def test_get_all_empty(self):
        """Test get_all returns empty list for empty registry."""
        registry = ModelRegistry()
        assert registry.get_all() == []

    def test_list_models(self):
        """Test list_models returns all model names."""
        registry = ModelRegistry()
        names = ["model-a", "model-b", "model-c"]

        for name in names:
            config = ModelConfig(name=name, api_base="https://example.com", api_key="key")
            tier = ModelTier(
                name=name,
                tier="standard",
                description="Test",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            )
            registry.register(config, tier)

        listed = registry.list_models()
        assert len(listed) == 3
        assert all(name in listed for name in names)

    def test_list_models_empty(self):
        """Test list_models returns empty list for empty registry."""
        registry = ModelRegistry()
        assert registry.list_models() == []

    def test_select_model_with_tier_preference(self):
        """Test select_model uses tier_preference when set."""
        registry = ModelRegistry()

        # Register all three tiers
        for tier_name in ["flash", "standard", "premium"]:
            config = ModelConfig(
                name=f"{tier_name}-model", api_base="https://example.com", api_key="key"
            )
            tier = ModelTier(
                name=f"{tier_name}-model",
                tier=tier_name,
                description=f"{tier_name} model",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            )
            registry.register(config, tier)

        # Test each tier preference
        for tier_name in ["flash", "standard", "premium"]:
            criteria = ModelSelectionCriteria(
                complexity=0.5, lambda_param=0.5, tier_preference=tier_name
            )
            model = registry.select_model(criteria)
            assert model.name == f"{tier_name}-model"

    def test_select_model_tier_preference_fallback(self):
        """Test select_model falls back to standard if preferred tier unavailable."""
        registry = ModelRegistry()

        # Only register standard tier
        config = ModelConfig(
            name="standard-model", api_base="https://example.com", api_key="key"
        )
        tier = ModelTier(
            name="standard-model",
            tier="standard",
            description="Standard",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )
        registry.register(config, tier)

        # Request flash (unavailable), should get standard
        criteria = ModelSelectionCriteria(
            complexity=0.5, lambda_param=0.5, tier_preference="flash"
        )
        model = registry.select_model(criteria)
        assert model.name == "standard-model"

    def test_select_model_high_complexity_low_lambda(self):
        """Test select_model selects premium for high complexity with low lambda."""
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

        # High complexity, low lambda (prefer accuracy)
        criteria = ModelSelectionCriteria(complexity=0.9, lambda_param=0.1)
        model = registry.select_model(criteria)
        assert model.name == "premium-model"

    def test_select_model_low_complexity_high_lambda(self):
        """Test select_model selects flash for low complexity with high lambda."""
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

        # Low complexity, high lambda (prefer cost)
        criteria = ModelSelectionCriteria(complexity=0.1, lambda_param=0.9)
        model = registry.select_model(criteria)
        assert model.name == "flash-model"

    def test_select_model_moderate_complexity(self):
        """Test select_model selects standard for moderate complexity."""
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

        # Moderate complexity
        criteria = ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)
        model = registry.select_model(criteria)
        assert model.name == "standard-model"

    def test_select_model_lambda_adjusts_thresholds(self):
        """Test select_model adjusts thresholds based on lambda."""
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

        # High lambda (0.9): prefer cost
        # Flash threshold: 0.2 + 0.9*0.3 = 0.47
        # Premium threshold: 0.8 - 0.9*0.3 = 0.53
        criteria = ModelSelectionCriteria(complexity=0.45, lambda_param=0.9)
        model = registry.select_model(criteria)
        assert model.name == "flash-model"

        # Low lambda (0.1): prefer accuracy
        # Flash threshold: 0.2 + 0.1*0.3 = 0.23
        # Premium threshold: 0.8 - 0.1*0.3 = 0.77
        criteria = ModelSelectionCriteria(complexity=0.8, lambda_param=0.1)
        model = registry.select_model(criteria)
        assert model.name == "premium-model"

    def test_select_model_no_models(self):
        """Test select_model raises ValueError when no models registered."""
        registry = ModelRegistry()
        criteria = ModelSelectionCriteria(complexity=0.5, lambda_param=0.5)

        with pytest.raises(ValueError, match="No models registered"):
            registry.select_model(criteria)

    def test_select_model_missing_tiers(self):
        """Test select_model handles missing tiers gracefully."""
        registry = ModelRegistry()

        # Only register standard
        config = ModelConfig(
            name="standard-model", api_base="https://example.com", api_key="key"
        )
        tier = ModelTier(
            name="standard-model",
            tier="standard",
            description="Standard",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )
        registry.register(config, tier)

        # Any complexity should return standard
        for complexity in [0.0, 0.5, 1.0]:
            criteria = ModelSelectionCriteria(complexity=complexity, lambda_param=0.5)
            model = registry.select_model(criteria)
            assert model.name == "standard-model"

    def test_len(self):
        """Test __len__ returns correct count."""
        registry = ModelRegistry()
        assert len(registry) == 0

        for i in range(3):
            config = ModelConfig(
                name=f"model-{i}", api_base="https://example.com", api_key="key"
            )
            tier = ModelTier(
                name=f"model-{i}",
                tier="standard",
                description="Test",
                cost_per_1k_input=0.001,
                cost_per_1k_output=0.002,
            )
            registry.register(config, tier)
            assert len(registry) == i + 1

    def test_contains(self):
        """Test __contains__ checks membership."""
        registry = ModelRegistry()
        assert "test" not in registry

        config = ModelConfig(name="test", api_base="https://example.com", api_key="key")
        tier = ModelTier(
            name="test",
            tier="standard",
            description="Test",
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
        )
        registry.register(config, tier)

        assert "test" in registry
        assert "nonexistent" not in registry


class TestGetBuiltinModels:
    """Tests for get_builtin_models function."""

    def test_returns_three_models(self):
        """Test get_builtin_models returns 3 model configurations."""
        models = get_builtin_models()
        assert len(models) == 3

    def test_returns_model_and_tier_tuples(self):
        """Test get_builtin_models returns (ModelConfig, ModelTier) tuples."""
        models = get_builtin_models()

        for config, tier in models:
            assert isinstance(config, ModelConfig)
            assert isinstance(tier, ModelTier)
            assert config.name == tier.name

    def test_model_names(self):
        """Test built-in models have correct names."""
        models = get_builtin_models()
        names = [config.name for config, _ in models]

        assert "glm-4-flash" in names
        assert "glm-4.7" in names
        assert "glm-4-plus" in names

    def test_model_tiers(self):
        """Test built-in models have correct tiers."""
        models = get_builtin_models()

        tier_map = {config.name: tier for config, tier in models}
        assert tier_map["glm-4-flash"].tier == "flash"
        assert tier_map["glm-4.7"].tier == "standard"
        assert tier_map["glm-4-plus"].tier == "premium"

    def test_model_cost_rates(self):
        """Test built-in models have positive cost rates."""
        models = get_builtin_models()

        for _, tier in models:
            assert tier.cost_per_1k_input > 0.0
            assert tier.cost_per_1k_output > 0.0

    def test_model_capabilities(self):
        """Test built-in models have capabilities lists."""
        models = get_builtin_models()

        for _, tier in models:
            assert isinstance(tier.capabilities, list)
            assert len(tier.capabilities) > 0

    def test_model_descriptions(self):
        """Test built-in models have descriptions."""
        models = get_builtin_models()

        for _, tier in models:
            assert tier.description
            assert len(tier.description) > 0

    def test_custom_cost_rates(self):
        """Test get_builtin_models accepts custom cost_rates."""
        custom_rates = {
            "glm-4-flash": {"input": 0.00005, "output": 0.0001},
            "glm-4.7": {"input": 0.0005, "output": 0.001},
        }

        models = get_builtin_models(cost_rates=custom_rates)
        tier_map = {config.name: tier for config, tier in models}

        assert tier_map["glm-4-flash"].cost_per_1k_input == 0.00005
        assert tier_map["glm-4-flash"].cost_per_1k_output == 0.0001
        assert tier_map["glm-4.7"].cost_per_1k_input == 0.0005
        assert tier_map["glm-4.7"].cost_per_1k_output == 0.001

        # glm-4-plus should keep defaults (real Z.ai pricing: ~$0.70/1M = 0.0007/1K)
        assert tier_map["glm-4-plus"].cost_per_1k_input > 0.0005

    def test_models_can_be_registered(self):
        """Test all built-in models can be registered in ModelRegistry."""
        models = get_builtin_models()
        registry = ModelRegistry()

        for config, tier in models:
            registry.register(config, tier)

        assert len(registry) == 3
        assert "glm-4-flash" in registry
        assert "glm-4.7" in registry
        assert "glm-4-plus" in registry

    def test_default_api_configs(self):
        """Test built-in models have valid API configs."""
        models = get_builtin_models()

        for config, _ in models:
            assert config.api_base
            assert config.api_base.startswith("http")
            assert config.temperature == 0.7
            assert config.max_tokens > 0

    def test_flash_model_lower_cost_than_standard(self):
        """Test flash tier is cheaper than standard."""
        models = get_builtin_models()
        tier_map = {config.name: tier for config, tier in models}

        flash_input = tier_map["glm-4-flash"].cost_per_1k_input
        standard_input = tier_map["glm-4.7"].cost_per_1k_input
        flash_output = tier_map["glm-4-flash"].cost_per_1k_output
        standard_output = tier_map["glm-4.7"].cost_per_1k_output

        assert flash_input < standard_input
        assert flash_output < standard_output

    def test_premium_model_higher_cost_than_standard(self):
        """Test premium tier is more expensive than standard."""
        models = get_builtin_models()
        tier_map = {config.name: tier for config, tier in models}

        premium_input = tier_map["glm-4-plus"].cost_per_1k_input
        standard_input = tier_map["glm-4.7"].cost_per_1k_input
        premium_output = tier_map["glm-4-plus"].cost_per_1k_output
        standard_output = tier_map["glm-4.7"].cost_per_1k_output

        assert premium_input > standard_input
        assert premium_output > standard_output
