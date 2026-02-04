"""Model selection complexity estimation and model selection logic.

This module implements heuristics for estimating task complexity and
selecting appropriate models based on complexity and cost-performance
trade-offs.
"""

from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import ModelSelectionCriteria
from aorchestra.models.registry import ModelRegistry

# Complexity keywords and their weights
# Higher weight = higher complexity contribution
COMPLEXITY_KEYWORDS: dict[str, float] = {
    "analyze": 0.3,
    "optimization": 0.4,
    "optimize": 0.4,
    "reasoning": 0.3,
    "planning": 0.3,
    "strategy": 0.3,
    "implement": 0.2,
    "design": 0.3,
    "architecture": 0.3,
    "debug": 0.2,
    "refactor": 0.2,
    "algorithm": 0.3,
    "complex": 0.2,
    "multi-step": 0.3,
    "nested": 0.2,
    "recursive": 0.3,
    "asynchronous": 0.2,
    "concurrent": 0.2,
    "parallel": 0.2,
    "distributed": 0.3,
    "machine learning": 0.3,
    "deep learning": 0.3,
    "neural": 0.2,
    "database": 0.2,
    "api": 0.1,
    "integration": 0.2,
    "security": 0.3,
    "authentication": 0.2,
    "authorization": 0.2,
    "encryption": 0.2,
    "performance": 0.2,
    "scalability": 0.3,
}

# Complex tools and their weights
# Higher weight = higher complexity contribution
COMPLEX_TOOLS: dict[str, float] = {
    "code_execute": 0.3,
    "web_search": 0.2,
    "file_read": 0.1,
    "file_write": 0.1,
    "database_query": 0.3,
    "api_call": 0.2,
}


def estimate_complexity(
    instruction: str,
    tools: list[str],
    context_length: int,
) -> float:
    """Estimate task complexity based on instruction, tools, and context.

    Complexity score is a weighted sum of:
    - Instruction length (max 0.3)
    - Complexity keywords in instruction (max 0.3)
    - Complex tools being used (max 0.3)
    - Context size (max 0.1)

    Final score is capped at 1.0.

    Args:
        instruction: Task instruction text
        tools: List of tool names being used
        context_length: Length of context in characters

    Returns:
        Complexity score in [0.0, 1.0]

    Examples:
        >>> estimate_complexity("Add 2 + 2", [], 100)
        0.0  # Very simple task

        >>> estimate_complexity("Analyze and optimize the recursive algorithm for performance", ["code_execute"], 2000)
        ~0.8  # Complex task
    """
    score = 0.0
    instruction_lower = instruction.lower()

    # 1. Instruction length (max 0.3, normalized to 500 chars)
    length_score = min(len(instruction) / 500, 0.3)
    score += length_score

    # 2. Complexity keywords (max 0.3)
    keyword_score = 0.0
    for keyword, weight in COMPLEXITY_KEYWORDS.items():
        if keyword in instruction_lower:
            keyword_score = min(keyword_score + weight, 0.3)
    score += keyword_score

    # 3. Complex tools (max 0.3)
    tool_score = 0.0
    for tool in tools:
        if tool in COMPLEX_TOOLS:
            tool_score = min(tool_score + COMPLEX_TOOLS[tool], 0.3)
    score += tool_score

    # 4. Context size (max 0.1, normalized to 2000 chars)
    context_score = min(context_length / 2000, 0.1)
    score += context_score

    # Cap at 1.0
    return min(score, 1.0)


def select_model_by_criteria(
    criteria: ModelSelectionCriteria,
    model_registry: ModelRegistry,
) -> ModelConfig:
    """Select a model based on complexity and lambda parameters.

    Delegates to ModelRegistry.select_model() for the actual selection logic.

    Args:
        criteria: ModelSelectionCriteria with complexity, lambda, and tier_preference
        model_registry: ModelRegistry to select from

    Returns:
        Selected ModelConfig

    Raises:
        ValueError: If no models are available

    Note:
        This function is a convenience wrapper around ModelRegistry.select_model().
        The actual selection logic (thresholds, fallbacks) is in ModelRegistry.
    """
    return model_registry.select_model(criteria)
