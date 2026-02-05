"""Model registry for managing LLM model tiers and configurations.

This module implements ModelRegistry for registering and selecting models
based on tier (flash, standard, premium) and selection criteria (complexity,
lambda parameter). Follows the ToolRegistry pattern from item 003.
"""

from typing import Optional

from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import ModelSelectionCriteria, ModelTier


class ModelRegistry:
    """Registry for managing model configurations and tier metadata.

    Provides registration, lookup, and intelligent model selection based on
    task complexity and cost-performance trade-off (lambda parameter).
    """

    def __init__(self) -> None:
        """Initialize an empty model registry."""
        self._configs: dict[str, ModelConfig] = {}
        self._tiers: dict[str, ModelTier] = {}

    def register(self, config: ModelConfig, tier: ModelTier) -> None:
        """Register a model with its tier metadata.

        Args:
            config: ModelConfig with model configuration
            tier: ModelTier with tier and cost information

        Raises:
            ValueError: If config.name != tier.name or model already registered
        """
        if config.name != tier.name:
            raise ValueError(
                f"Config name '{config.name}' must match tier name '{tier.name}'"
            )

        if config.name in self._configs:
            raise ValueError(f"Model '{config.name}' is already registered")

        self._configs[config.name] = config
        self._tiers[tier.name] = tier

    def unregister(self, name: str) -> None:
        """Remove a model from the registry.

        Args:
            name: Name of the model to remove

        Raises:
            KeyError: If model not found
        """
        if name not in self._configs:
            raise KeyError(f"Model '{name}' not found in registry")

        del self._configs[name]
        del self._tiers[name]

    def get(self, name: str) -> Optional[ModelConfig]:
        """Get a model config by name.

        Args:
            name: Model name to look up

        Returns:
            ModelConfig if found, None otherwise
        """
        return self._configs.get(name)

    def get_tier(self, name: str) -> Optional[ModelTier]:
        """Get tier metadata for a model by name.

        Args:
            name: Model name to look up

        Returns:
            ModelTier if found, None otherwise
        """
        return self._tiers.get(name)

    def get_by_tier(self, tier: str) -> Optional[ModelConfig]:
        """Get the first model configuration at a specific tier.

        Args:
            tier: Tier level ('flash', 'standard', 'premium')

        Returns:
            ModelConfig at tier, None if no model at that tier
        """
        for model_name, model_tier in self._tiers.items():
            if model_tier.tier == tier:
                return self._configs[model_name]
        return None

    def get_all(self) -> list[ModelConfig]:
        """Get all registered model configurations.

        Returns:
            List of all ModelConfig objects (empty if registry empty)
        """
        return list(self._configs.values())

    def list_models(self) -> list[str]:
        """Get list of all registered model names.

        Returns:
            List of model names (empty if registry empty)
        """
        return list(self._configs.keys())

    def select_model(self, criteria: ModelSelectionCriteria) -> ModelConfig:
        """Select an appropriate model based on complexity and lambda.

        Model selection logic:
        - If tier_preference is set, tries to use that tier (falls back to standard)
        - Otherwise uses lambda-adjusted thresholds:
          - Higher lambda (0.9-1.0) = prefer cheaper models
          - Lower lambda (0.0-0.1) = prefer accurate models
          - Premium threshold: 0.8 - (lambda * 0.3) = 0.8 to 0.5
          - Flash threshold: 0.2 + (lambda * 0.3) = 0.2 to 0.5

        Args:
            criteria: ModelSelectionCriteria with complexity, lambda, tier_preference

        Returns:
            Selected ModelConfig

        Raises:
            ValueError: If no models are registered or selection fails
        """
        if len(self._configs) == 0:
            raise ValueError("No models registered in ModelRegistry")

        # If tier preference is set, try to use it
        if criteria.tier_preference:
            model = self.get_by_tier(criteria.tier_preference)
            if model:
                return model
            # Fall back to standard if preferred tier unavailable
            model = self.get_by_tier("standard")
            if model:
                return model

        # Calculate thresholds based on lambda
        # lambda: 0.0 = prefer accuracy, 1.0 = prefer cost
        premium_threshold = 0.8 - (criteria.lambda_param * 0.3)  # 0.8 to 0.5
        flash_threshold = 0.2 + (criteria.lambda_param * 0.3)  # 0.2 to 0.5

        # Select based on complexity
        if criteria.complexity >= premium_threshold:
            # High complexity: use premium
            model = self.get_by_tier("premium")
            if model:
                return model
        elif criteria.complexity <= flash_threshold:
            # Low complexity: use flash
            model = self.get_by_tier("flash")
            if model:
                return model

        # Moderate complexity or fallback: use standard
        model = self.get_by_tier("standard")
        if model:
            return model

        # Last resort: return any available model
        return list(self._configs.values())[0]

    def __len__(self) -> int:
        """Get number of registered models."""
        return len(self._configs)

    def __contains__(self, name: str) -> bool:
        """Check if model is registered."""
        return name in self._configs


def get_builtin_models(
    cost_rates: Optional[dict[str, dict[str, float]]] = None,
) -> list[tuple[ModelConfig, ModelTier]]:
    """Get built-in model configurations and tier metadata.

    Returns default models for flash, standard, and premium tiers with
    estimated cost rates. Cost rates can be overridden with custom values.

    Args:
        cost_rates: Optional dict mapping model names to cost rates
            Format: {"model_name": {"input": float, "output": float}}
            Defaults to estimated rates for Z.ai models

    Returns:
        List of (ModelConfig, ModelTier) tuples for built-in models

    Note:
        Cost rates are estimates and should be updated with actual Z.ai pricing
        when available. See https://z.ai/pricing for current rates.
    """
    # Default estimated cost rates (in USD per 1K tokens)
    defaults: dict[str, dict[str, float]] = {
        # Real Z.ai/Zhipu pricing per 1M tokens (converted to per 1K)
        # GLM-4-Flash: budget tier
        "glm-4-flash": {"input": 0.0001, "output": 0.0005},
        # GLM-4.7: ~$0.10-0.24/1M input, ~$1.74/1M output
        "glm-4.7": {"input": 0.00024, "output": 0.00174},
        # GLM-4-Plus: ~$0.70/1M input
        "glm-4-plus": {"input": 0.0007, "output": 0.0035},
    }

    # Use custom rates if provided
    rates = {**defaults}
    if cost_rates:
        for model_name, model_rates in cost_rates.items():
            if model_name in rates:
                rates[model_name] = model_rates

    # Create model configs and tier metadata
    models = [
        (
            ModelConfig(
                name="glm-4-flash",
                api_base="https://open.bigmodel.cn/api/paas/v4/",
                api_key="",
                temperature=0.7,
                max_tokens=1024,
            ),
            ModelTier(
                name="glm-4-flash",
                tier="flash",
                description="Fast and cost-effective model for simple tasks like calculations, data formatting, and basic text processing",
                cost_per_1k_input=rates["glm-4-flash"]["input"],
                cost_per_1k_output=rates["glm-4-flash"]["output"],
                capabilities=["text", "simple_math", "formatting"],
            ),
        ),
        (
            ModelConfig(
                name="glm-4.7",
                api_base="https://open.bigmodel.cn/api/paas/v4/",
                api_key="",
                temperature=0.7,
                max_tokens=2048,
            ),
            ModelTier(
                name="glm-4.7",
                tier="standard",
                description="Balanced model for general reasoning, moderate complexity tasks, and everyday use",
                cost_per_1k_input=rates["glm-4.7"]["input"],
                cost_per_1k_output=rates["glm-4.7"]["output"],
                capabilities=["text", "reasoning", "math", "code", "analysis"],
            ),
        ),
        (
            ModelConfig(
                name="glm-4-plus",
                api_base="https://open.bigmodel.cn/api/paas/v4/",
                api_key="",
                temperature=0.7,
                max_tokens=4096,
            ),
            ModelTier(
                name="glm-4-plus",
                tier="premium",
                description="High-end model for complex reasoning, code generation, multi-step planning, and advanced analysis",
                cost_per_1k_input=rates["glm-4-plus"]["input"],
                cost_per_1k_output=rates["glm-4-plus"]["output"],
                capabilities=[
                    "text",
                    "advanced_reasoning",
                    "code_generation",
                    "planning",
                    "analysis",
                    "optimization",
                ],
            ),
        ),
    ]

    return models
