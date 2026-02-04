"""AOrchestra: Open Implementation of Agentic Orchestration.

Any agent is a dynamically instantiable 4-tuple:
    Φ = (Instruction, Context, Tools, Model)
"""

__version__ = "0.1.0"

# Core components (Item 001)
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.core.agents import SubAgent
from aorchestra.core.factory import AgentFactory
from aorchestra.core.orchestrator import Orchestrator

# Models (Item 001, Item 004)
from aorchestra.models.config import ModelConfig

# Cost tracking (Item 004)
from aorchestra.models.cost import (
    CostRecord,
    CostTracker,
    ModelTier,
    ModelSelectionCriteria,
)

# Model registry (Item 004)
from aorchestra.models.registry import ModelRegistry, get_builtin_models

# Orchestrator state and actions (Item 001, Item 003, Item 004)
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction

# Context curation (Item 003)
from aorchestra.orchestrator.context import (
    score_relevance,
    select_relevant_history,
    build_context_for_subtask,
    extract_keywords_from_instruction,
)

# Complexity estimation (Item 004)
from aorchestra.orchestrator.selection import (
    estimate_complexity,
    select_model_by_criteria,
)

# Tools (Item 002, Item 003)
from aorchestra.tools import ToolRegistry, get_builtin_tools_metadata

__all__ = [
    "__version__",
    # Core (Item 001)
    "AgentTuple",
    "Observation",
    "SubAgent",
    "AgentFactory",
    "Orchestrator",
    # Models (Item 001)
    "ModelConfig",
    # Cost tracking (Item 004)
    "CostRecord",
    "CostTracker",
    "ModelTier",
    "ModelSelectionCriteria",
    # Model registry (Item 004)
    "ModelRegistry",
    "get_builtin_models",
    # State and actions (Item 001, Item 003, Item 004)
    "OrchestratorState",
    "Delegation",
    "DelegateAction",
    "FinishAction",
    # Context curation (Item 003)
    "score_relevance",
    "select_relevant_history",
    "build_context_for_subtask",
    "extract_keywords_from_instruction",
    # Complexity estimation (Item 004)
    "estimate_complexity",
    "select_model_by_criteria",
    # Tools (Item 002, Item 003)
    "ToolRegistry",
    "get_builtin_tools_metadata",
]
