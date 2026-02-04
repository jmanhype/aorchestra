"""Orchestrator module for task delegation and decision-making.

Item 001: Core orchestrator components
Item 003: Context curation for intelligent context filtering
Item 004: Complexity estimation and model selection
"""

from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.orchestrator.context import (
    score_relevance,
    select_relevant_history,
    build_context_for_subtask,
    extract_keywords_from_instruction,
)
from aorchestra.orchestrator.selection import (
    estimate_complexity,
    select_model_by_criteria,
)

__all__ = [
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
]
