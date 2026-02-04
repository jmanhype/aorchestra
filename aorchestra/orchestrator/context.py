"""Context curation for Orchestrator.

Item 003: Intelligent filtering of relevant context for sub-agents.
"""

import re
from typing import Any

from aorchestra.orchestrator.state import Delegation


def score_relevance(text: str, keywords: list[str]) -> float:
    """Score text relevance based on keyword frequency.

    Simple scoring algorithm:
    - Count keyword occurrences (case-insensitive)
    - Exact matches get higher score
    - Partial matches get partial score

    Args:
        text: Text to score.
        keywords: Keywords to search for.

    Returns:
        Relevance score (higher = more relevant).
    """
    if not keywords or not text:
        return 0.0

    text_lower = text.lower()
    score = 0.0

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # Exact word match (higher weight)
        word_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        exact_matches = len(re.findall(word_pattern, text_lower))
        score += exact_matches * 2.0

        # Partial match (lower weight) - find substring occurrences
        # Count occurrences of keyword as substring anywhere in text
        # This will match even if it's part of a word
        partial_matches = text_lower.count(keyword_lower)
        score += partial_matches * 0.5

    return score


def extract_keywords_from_instruction(instruction: str) -> list[str]:
    """Extract relevant keywords from an instruction.

    Simple extraction: identify nouns and technical terms.
    For now, split by common delimiters and filter stopwords.

    Args:
        instruction: Instruction text.

    Returns:
        List of keywords.
    """
    if not instruction:
        return []

    # Common stopwords to filter
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "as", "is", "was", "are",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must",
        "please", "help", "need", "want", "use", "make", "get",
        "this", "that", "these", "those", "it", "its", "not", "no",
        "over", "under", "through", "during", "before", "after",
    }

    # Split by common delimiters - match alphabetic words including underscores
    words = re.findall(r'\b[a-zA-Z_]{3,}\b', instruction.lower())

    # Filter stopwords and short words
    keywords = [w for w in words if w not in stopwords]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def select_relevant_history(
    history: list[Delegation],
    keywords: list[str] | None = None,
    max_items: int = 5,
    include_recent: int = 2,
) -> list[Delegation]:
    """Select relevant items from delegation history.

    Combines recent items (always included) with keyword-relevant items.

    Args:
        history: List of Delegation records.
        keywords: Keywords for relevance scoring.
        max_items: Maximum items to return.
        include_recent: Number of most recent items to always include.

    Returns:
        List of selected Delegation records, ordered by relevance.
    """
    if not history:
        return []

    # Always include recent items
    recent_items = history[-include_recent:] if include_recent > 0 else []
    recent_indices = {id(d) for d in recent_items}

    # Score remaining items by keyword relevance
    keywords = keywords or []

    # If no keywords provided, return up to max_items from history
    if not keywords:
        return history[:max_items]

    scored = []

    for delegation in history[:-include_recent] if include_recent > 0 else history:
        # Skip if already in recent items
        if id(delegation) in recent_indices:
            continue

        # Build text from observation summary and instruction
        text = (
            delegation.observation.result_summary + " " +
            delegation.tuple.instruction
        )

        score = score_relevance(text, keywords)
        scored.append((delegation, score))

    # Sort by score (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Select top scored items
    top_scored = [d for d, s in scored][:max_items - len(recent_items)]

    # Combine: recent items first, then scored items
    selected = recent_items + top_scored

    # Limit to max_items
    return selected[:max_items]


def build_context_for_subtask(
    action_context: str,
    history: list[Delegation],
    keywords: list[str] | None = None,
    max_history_items: int = 3,
) -> str:
    """Build context string for a subtask.

    Combines action-specific context with relevant history.

    Args:
        action_context: Context from DelegateAction.
        history: Delegation history.
        keywords: Keywords for relevance scoring.
        max_history_items: Max history items to include.

    Returns:
        Formatted context string.
    """
    parts = []

    # Add action-specific context
    if action_context:
        parts.append(action_context)

    # Add relevant history
    if history:
        selected = select_relevant_history(
            history=history,
            keywords=keywords,
            max_items=max_history_items,
            include_recent=max(1, max_history_items // 2),
        )

        if selected:
            parts.append("\n**Relevant Previous Work:**")
            for delegation in selected:
                parts.append(
                    f"- {delegation.observation.result_summary}"
                )

    return "\n".join(parts) if parts else ""
