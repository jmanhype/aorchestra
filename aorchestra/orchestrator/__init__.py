"""Orchestrator module for task delegation and decision-making.

Item 001: Core orchestrator components
Item 003: Context curation for intelligent context filtering
"""

from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.orchestrator.context import (
    score_relevance,
    select_relevant_history,
    build_context_for_subtask,
    extract_keywords_from_instruction,
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
]
