"""Test US-009 through US-012 acceptance criteria for context curation"""

from aorchestra.orchestrator import (
    score_relevance,
    extract_keywords_from_instruction,
    select_relevant_history,
    build_context_for_subtask,
)
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.orchestrator.state import Delegation
from aorchestra.models.config import ModelConfig


def test_score_relevance():
    """Test US-009: context.score_relevance() function"""
    print("\n" + "=" * 60)
    print("Testing US-009: context.score_relevance() function")
    print("=" * 60)

    # Test: Takes text and list of keywords as parameters
    print("\nTest 1: Function signature")
    result = score_relevance("test text", ["test"])
    assert isinstance(result, float)
    print("  [OK] Takes text and list of keywords, returns float")

    # Test: Returns float score (higher = more relevant)
    print("\nTest 2: Returns float score")
    result = score_relevance("test", ["test"])
    assert isinstance(result, float)
    print("  [OK] Returns float score")

    # Test: Returns 0.0 for empty text or empty keywords
    print("\nTest 3: Empty inputs return 0.0")
    assert score_relevance("", ["test"]) == 0.0
    print("  [OK] Empty text returns 0.0")
    assert score_relevance("test", []) == 0.0
    print("  [OK] Empty keywords returns 0.0")

    # Test: Exact word matches (word boundary) have weight 2.0
    print("\nTest 4: Exact word matches have weight 2.0")
    result = score_relevance("test", ["test"])
    assert result == 2.0
    print("  [OK] Single exact match = 2.0")

    result = score_relevance("test test test", ["test"])
    assert result == 6.0
    print("  [OK] Three exact matches = 6.0")

    # Test: Partial matches (substring) have weight 0.5
    print("\nTest 5: Partial matches have weight 0.5")
    result = score_relevance("testing", ["test"])
    # "test" is a substring of "testing", not a word match
    # The word "testing" doesn't match word boundary, so it's a partial match
    assert result == 0.5
    print("  [OK] Partial match = 0.5")

    # Test: Scoring is case-insensitive
    print("\nTest 6: Case-insensitive")
    assert score_relevance("TEST", ["test"]) == 2.0
    print("  [OK] 'TEST' matches 'test'")
    assert score_relevance("test", ["TEST"]) == 2.0
    print("  [OK] 'test' matches 'TEST'")
    assert score_relevance("Test", ["test"]) == 2.0
    print("  [OK] 'Test' matches 'test'")

    # Test: Multiple occurrences of same keyword are cumulative
    print("\nTest 7: Multiple occurrences cumulative")
    result = score_relevance("test test", ["test"])
    assert result == 4.0
    print("  [OK] Two exact matches = 4.0")

    # Test: Multiple keywords are cumulative
    print("\nTest 8: Multiple keywords cumulative")
    result = score_relevance("python code", ["python", "code"])
    assert result == 4.0
    print("  [OK] Two keywords with one match each = 4.0")

    result = score_relevance("python and code", ["python", "code", "test"])
    assert result == 4.0
    print("  [OK] Third keyword with no match doesn't affect score")

    print("\nUS-009: All tests passed!")


def test_extract_keywords_from_instruction():
    """Test US-010: context.extract_keywords_from_instruction() function"""
    print("\n" + "=" * 60)
    print("Testing US-010: context.extract_keywords_from_instruction() function")
    print("=" * 60)

    # Test: Takes instruction string as parameter
    print("\nTest 1: Function signature")
    result = extract_keywords_from_instruction("test instruction")
    assert isinstance(result, list)
    print("  [OK] Takes instruction string, returns list")

    # Test: Returns list of keywords (lowercase strings)
    print("\nTest 2: Returns lowercase list")
    result = extract_keywords_from_instruction("Test Instruction Python")
    assert all(isinstance(k, str) for k in result)
    assert all(k.islower() for k in result)
    print("  [OK] Returns list of lowercase strings")

    # Test: Returns empty list for empty input
    print("\nTest 3: Empty input returns empty list")
    assert extract_keywords_from_instruction("") == []
    print("  [OK] Empty string returns empty list")
    assert extract_keywords_from_instruction(None) == []
    print("  [OK] None returns empty list")

    # Test: Filters out common stopwords
    print("\nTest 4: Filters stopwords")
    result = extract_keywords_from_instruction("the quick brown fox jumps over the lazy dog")
    assert "the" not in result
    assert "over" not in result
    print("  [OK] Removes common stopwords")

    # Test: Filters out words shorter than 3 characters
    print("\nTest 5: Filters short words")
    result = extract_keywords_from_instruction("an at by")
    assert result == []
    print("  [OK] Filters words shorter than 3 characters")

    # Test: Keeps technical terms and relevant nouns
    print("\nTest 6: Keeps relevant words")
    result = extract_keywords_from_instruction("Write Python code to calculate fibonacci")
    assert "write" in result
    assert "python" in result
    assert "code" in result
    assert "calculate" in result
    assert "fibonacci" in result
    print("  [OK] Keeps technical terms and nouns")

    # Test: Uses regex to extract words (\b[a-zA-Z]{3,}\b)
    print("\nTest 7: Regex word extraction")
    result = extract_keywords_from_instruction("Test123")
    assert "test" not in result  # Digits not included
    print("  [OK] Regex extracts only alphabetic words")

    result = extract_keywords_from_instruction("hello world!")
    assert "hello" in result
    assert "world" in result
    print("  [OK] Extracts words from punctuation")

    print("\nUS-010: All tests passed!")


def test_select_relevant_history():
    """Test US-011: context.select_relevant_history() function"""
    print("\n" + "=" * 60)
    print("Testing US-011: context.select_relevant_history() function")
    print("=" * 60)

    # Create mock delegation history
    def make_delegation(instruction: str, summary: str, step: int = 0) -> Delegation:
        """Create a mock Delegation for testing."""
        from datetime import datetime
        return Delegation(
            step=step,
            tuple=AgentTuple(
                instruction=instruction,
                context="",
                tools=[],
                model=ModelConfig(name="test", api_base="http://test"),
            ),
            observation=Observation(
                result=summary,
                result_summary=summary,
                error_logs=[],
                execution_time=1.0,
                tool_calls=[],
                timestamp=datetime.now().isoformat(),
            ),
            timestamp=datetime.now().isoformat(),
        )

    history = [
        make_delegation("Calculate fibonacci sequence", "Computed fibonacci(10) = 55", step=1),
        make_delegation("Sort array", "Sorted array [3, 1, 2] to [1, 2, 3]", step=2),
        make_delegation("Write Python code", "Created Python script for data processing", step=3),
        make_delegation("Test application", "Ran unit tests - all passed", step=4),
        make_delegation("Analyze data", "Processed 1000 records, found 5 outliers", step=5),
    ]

    # Test: Takes history list, keywords, max_items, include_recent as parameters
    print("\nTest 1: Function signature")
    result = select_relevant_history(history, keywords=["test"], max_items=3, include_recent=2)
    assert isinstance(result, list)
    print("  [OK] Accepts history, keywords, max_items, include_recent")

    # Test: Returns list of selected Delegation records
    print("\nTest 2: Returns list")
    result = select_relevant_history(history)
    assert isinstance(result, list)
    print("  [OK] Returns list")

    # Test: Handles empty history (returns empty list)
    print("\nTest 3: Empty history")
    result = select_relevant_history([])
    assert result == []
    print("  [OK] Returns empty list for empty history")

    # Test: Always includes recent items (include_recent parameter)
    print("\nTest 4: Always includes recent items")
    result = select_relevant_history(history, include_recent=2)
    assert len(result) >= 2
    # Last 2 items should be in result
    assert result[-1] == history[-1]
    assert result[-2] == history[-2]
    print("  [OK] Includes recent items")

    # Test: Scores remaining items by keyword relevance using score_relevance()
    print("\nTest 5: Scoring by keyword relevance")
    result = select_relevant_history(history, keywords=["python"], max_items=3, include_recent=1)
    # Should include the Python-related delegation
    python_items = [d for d in result if "python" in d.tuple.instruction.lower()]
    assert len(python_items) > 0
    print("  [OK] Scores by keyword relevance")

    # Test: Combines recent items + top-scored items
    print("\nTest 6: Combines recent + scored")
    result = select_relevant_history(history, keywords=["data"], max_items=4, include_recent=2)
    assert len(result) <= 4
    # Check that recent items are included
    assert history[-1] in result
    print("  [OK] Combines recent and scored items")

    # Test: Respects max_items limit on final result
    print("\nTest 7: max_items limit")
    result = select_relevant_history(history, max_items=2)
    assert len(result) <= 2
    print("  [OK] Respects max_items limit")

    # Test: Items are ordered: recent first, then by relevance score
    print("\nTest 8: Ordering")
    result = select_relevant_history(history, keywords=["test"], max_items=4, include_recent=1)
    # First item should be most recent
    assert result[0] == history[-1]
    print("  [OK] Recent items first")

    # Test: Skips items already in recent list when scoring
    print("\nTest 9: No duplicates from recent")
    result = select_relevant_history(history, max_items=5, include_recent=2)
    # Check no duplicates (using id)
    ids = [id(d) for d in result]
    assert len(ids) == len(set(ids))
    print("  [OK] No duplicates in result")

    print("\nUS-011: All tests passed!")


def test_build_context_for_subtask():
    """Test US-012: context.build_context_for_subtask() function"""
    print("\n" + "=" * 60)
    print("Testing US-012: context.build_context_for_subtask() function")
    print("=" * 60)

    # Create mock delegation history
    def make_delegation(instruction: str, summary: str, step: int = 0) -> Delegation:
        """Create a mock Delegation for testing."""
        from datetime import datetime
        return Delegation(
            step=step,
            tuple=AgentTuple(
                instruction=instruction,
                context="",
                tools=[],
                model=ModelConfig(name="test", api_base="http://test"),
            ),
            observation=Observation(
                result=summary,
                result_summary=summary,
                error_logs=[],
                execution_time=1.0,
                tool_calls=[],
                timestamp=datetime.now().isoformat(),
            ),
            timestamp=datetime.now().isoformat(),
        )

    history = [
        make_delegation("Calculate fibonacci", "Computed fibonacci(10) = 55", step=1),
        make_delegation("Sort array", "Sorted array [3, 1, 2] to [1, 2, 3]", step=2),
    ]

    # Test: Takes action_context, history, keywords, max_history_items as parameters
    print("\nTest 1: Function signature")
    result = build_context_for_subtask("context", history, ["test"], 2)
    assert isinstance(result, str)
    print("  [OK] Accepts all parameters")

    # Test: Returns formatted context string
    print("\nTest 2: Returns string")
    result = build_context_for_subtask("context", history)
    assert isinstance(result, str)
    print("  [OK] Returns string")

    # Test: Includes action_context if provided
    print("\nTest 3: Includes action_context")
    result = build_context_for_subtask("Action context here", [])
    assert "Action context here" in result
    print("  [OK] Includes action_context")

    # Test: Adds '**Relevant Previous Work:**' header if history included
    print("\nTest 4: History header")
    result = build_context_for_subtask("", history)
    assert "**Relevant Previous Work:**" in result
    print("  [OK] Adds history header")

    # Test: Uses select_relevant_history() to filter history
    print("\nTest 5: Uses select_relevant_history")
    result = build_context_for_subtask("", history, max_history_items=1)
    assert result.count("-") == 1  # Only one bullet point
    print("  [OK] Filters history with max_history_items")

    # Test: Passes keywords and max_history_items to selection
    print("\nTest 6: Passes selection parameters")
    result = build_context_for_subtask("", history, keywords=["fibonacci"], max_history_items=2)
    # Should filter by keywords
    assert "fibonacci" in result.lower()
    print("  [OK] Passes keywords to selection")

    # Test: Formats each observation as bullet point with result_summary
    print("\nTest 7: Formats observations as bullets")
    result = build_context_for_subtask("", history)
    # Check for bullet points
    assert "- " in result
    # Check for result summaries
    assert "fibonacci" in result.lower()
    assert "sorted" in result.lower()
    print("  [OK] Formats as bullet points")

    # Test: Returns empty string if no action_context and no history
    print("\nTest 8: Empty inputs return empty string")
    result = build_context_for_subtask("", [])
    assert result == ""
    print("  [OK] Empty inputs return empty string")

    print("\nUS-012: All tests passed!")


def main():
    """Run all context curation tests"""
    test_score_relevance()
    test_extract_keywords_from_instruction()
    test_select_relevant_history()
    test_build_context_for_subtask()

    print("\n" + "=" * 60)
    print("ALL US-009 through US-012 TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
