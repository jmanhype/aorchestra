"""Cost tracking models for monitoring token usage and monetary costs.

This module defines Pydantic models for tracking token usage, estimated costs,
and model tier information. These models are used throughout the system for
cost-aware model routing and cost monitoring.
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CostRecord(BaseModel):
    """Record of token usage and estimated cost for a single LLM call.

    Tracks the number of tokens used (prompt, completion, total) and the
    estimated monetary cost based on model tier pricing. Used by CostTracker
    to aggregate costs across delegations.
    """

    model_name: str = Field(
        ...,
        description="Name of the model used (e.g., 'glm-4-flash', 'glm-4.7')",
    )
    prompt_tokens: int = Field(
        ...,
        ge=0,
        description="Number of tokens in the input prompt",
    )
    completion_tokens: int = Field(
        ...,
        ge=0,
        description="Number of tokens in the generated completion",
    )
    total_tokens: int = Field(
        ...,
        ge=0,
        description="Total tokens used (prompt + completion)",
    )
    estimated_cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Estimated cost in USD based on token usage and model tier rates",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp of when the cost was recorded",
    )

    @classmethod
    def from_openai_usage(
        cls,
        model_name: str,
        usage: object,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
    ) -> "CostRecord":
        """Create a CostRecord from an OpenAI API response.usage object.

        Args:
            model_name: Name of the model used
            usage: OpenAI response.usage object with prompt_tokens, completion_tokens, total_tokens
            cost_per_1k_input: Cost per 1,000 input tokens in USD
            cost_per_1k_output: Cost per 1,000 output tokens in USD

        Returns:
            CostRecord with token counts and estimated cost

        Note:
            If usage is None or attributes are missing, estimates tokens based on input length.
        """
        try:
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)
        except AttributeError:
            # usage object doesn't have expected attributes
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

        # Calculate estimated cost
        estimated_cost_usd = (prompt_tokens / 1000) * cost_per_1k_input + (
            completion_tokens / 1000
        ) * cost_per_1k_output

        return cls(
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )


class ModelTier(BaseModel):
    """Metadata about a model's tier, capabilities, and cost rates.

    Associates a model configuration with its tier (flash, standard, premium),
    cost rates, and capabilities. Used by ModelRegistry for model selection.
    """

    name: str = Field(
        ...,
        description="Model name (must match ModelConfig.name)",
    )
    tier: Literal["flash", "standard", "premium"] = Field(
        ...,
        description="Model tier level (flash=cheap/fast, standard=balanced, premium=capable)",
    )
    description: str = Field(
        ...,
        description="Description of the model and its use cases",
    )
    cost_per_1k_input: float = Field(
        ...,
        gt=0.0,
        description="Cost per 1,000 input tokens in USD",
    )
    cost_per_1k_output: float = Field(
        ...,
        gt=0.0,
        description="Cost per 1,000 output tokens in USD",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="List of capabilities (e.g., ['code', 'reasoning', 'math'])",
    )


class ModelSelectionCriteria(BaseModel):
    """Criteria for selecting an appropriate model based on task complexity.

    Used by ModelRegistry.select_model() to choose between model tiers based
    on task complexity and the cost-performance trade-off parameter (lambda).
    """

    complexity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated task complexity (0.0 = simple, 1.0 = complex)",
    )
    lambda_param: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Cost-performance trade-off (0.0 = prefer accuracy, 1.0 = prefer cost)",
    )
    tier_preference: Optional[Literal["flash", "standard", "premium"]] = Field(
        default=None,
        description="Optional override to force selection of a specific tier",
    )


class CostTracker:
    """Aggregates and summarizes cost records across multiple LLM calls.

    Tracks cost records from delegations and provides summary statistics
    including total cost, total tokens, and per-model breakdowns.
    """

    def __init__(self) -> None:
        """Initialize an empty cost tracker."""
        self._records: list[CostRecord] = []

    def track(self, record: CostRecord) -> None:
        """Add a cost record to tracking.

        Args:
            record: CostRecord to add to the tracker
        """
        self._records.append(record)

    def get_total_cost(self) -> float:
        """Get total estimated cost across all tracked records.

        Returns:
            Sum of estimated_cost_usd from all records (0.0 if no records)
        """
        return sum(r.estimated_cost_usd for r in self._records)

    def get_total_tokens(self) -> int:
        """Get total token count across all tracked records.

        Returns:
            Sum of total_tokens from all records (0 if no records)
        """
        return sum(r.total_tokens for r in self._records)

    def get_delegation_count(self) -> int:
        """Get number of tracked delegations.

        Returns:
            Number of cost records being tracked
        """
        return len(self._records)

    def get_summary(self) -> dict:
        """Get comprehensive cost summary with breakdown per model.

        Returns:
            Dict with total_cost_usd, total_tokens, delegation_count, model_breakdown
        """
        model_breakdown: dict[str, dict[str, float]] = {}
        for record in self._records:
            model = record.model_name
            if model not in model_breakdown:
                model_breakdown[model] = {
                    "cost_usd": 0.0,
                    "tokens": 0,
                    "calls": 0,
                }
            model_breakdown[model]["cost_usd"] += record.estimated_cost_usd
            model_breakdown[model]["tokens"] += record.total_tokens
            model_breakdown[model]["calls"] += 1

        return {
            "total_cost_usd": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "delegation_count": self.get_delegation_count(),
            "model_breakdown": model_breakdown,
        }

    def reset(self) -> None:
        """Clear all cost records from the tracker."""
        self._records.clear()

    def get_records(self) -> list[CostRecord]:
        """Get a copy of all tracked cost records.

        Returns:
            Copy of the records list (modifications don't affect tracker)
        """
        return list(self._records)
