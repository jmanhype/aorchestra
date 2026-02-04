"""Tests for context curation module (Item 003)."""

import pytest

from aorchestra.orchestrator.context import (
    score_relevance,
    extract_keywords_from_instruction,
    select_relevant_history,
    build_context_for_subtask,
)
from aorchestra.orchestrator.state import Delegation
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.models.cost import CostRecord


def _make_model():
    return ModelConfig(name="test-model", api_base="http://test")


def _make_cost_record():
    return CostRecord(
        model_name="test-model",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.001,
    )


class TestScoreRelevance:
    """Tests for score_relevance function."""

    def test_no_keywords_returns_zero(self):
        score = score_relevance("some text", [])
        assert score == 0.0

    def test_empty_text_returns_zero(self):
        score = score_relevance("", ["keyword"])
        assert score == 0.0

    def test_both_empty_returns_zero(self):
        score = score_relevance("", [])
        assert score == 0.0

    def test_exact_word_match_weight(self):
        # "python" exact word match = 2.0, plus partial substring match = 0.5
        score = score_relevance("python programming", ["python"])
        assert score == 2.5  # 2.0 exact + 0.5 partial (substring count=1)

    def test_partial_match_weight(self):
        # "py" is substring of "python" but not a word boundary match
        score = score_relevance("python programming", ["py"])
        assert score == 0.5  # 0 exact + 0.5 partial (1 occurrence)

    def test_case_insensitive(self):
        score1 = score_relevance("Python programming", ["python"])
        score2 = score_relevance("PYTHON PROGRAMMING", ["PYTHON"])
        score3 = score_relevance("python programming", ["PYTHON"])
        assert score1 == score2 == score3

    def test_cumulative_multiple_occurrences(self):
        # "python" appears twice as exact word
        score = score_relevance("python is great and python is awesome", ["python"])
        # 2 exact matches * 2.0 = 4.0, plus 2 substring matches * 0.5 = 1.0
        assert score == 5.0

    def test_cumulative_multiple_keywords(self):
        # "python" once exact, "async" once exact
        score = score_relevance("python async programming", ["python", "async"])
        # python: 2.0 exact + 0.5 partial = 2.5
        # async: 2.0 exact + 0.5 partial = 2.5
        assert score == 5.0

    def test_no_match_returns_zero(self):
        score = score_relevance("hello world", ["python", "async"])
        assert score == 0.0

    def test_word_boundary_detection(self):
        # "code" exact in "code" = 1, partial in "code", "encode", "decoder" = 3
        score = score_relevance("code encode decoder", ["code"])
        # 1 exact * 2.0 + 3 partial * 0.5 = 2.0 + 1.5 = 3.5
        assert score == 3.5


class TestExtractKeywordsFromInstruction:
    """Tests for extract_keywords_from_instruction function."""

    def test_empty_input_returns_empty_list(self):
        keywords = extract_keywords_from_instruction("")
        assert keywords == []

    def test_none_input_returns_empty_list(self):
        keywords = extract_keywords_from_instruction(None)
        assert keywords == []

    def test_filters_short_words(self):
        keywords = extract_keywords_from_instruction("a an at to do it is")
        assert keywords == []

    def test_filters_common_stopwords(self):
        keywords = extract_keywords_from_instruction(
            "the quick brown fox jumps over the lazy dog and runs fast"
        )
        assert "the" not in keywords
        assert "and" not in keywords
        assert "over" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords
        assert "jumps" in keywords
        assert "runs" in keywords

    def test_keeps_technical_terms(self):
        keywords = extract_keywords_from_instruction(
            "Use python asyncio for async programming"
        )
        assert "python" in keywords
        assert "asyncio" in keywords
        assert "async" in keywords
        assert "programming" in keywords

    def test_returns_lowercase(self):
        keywords = extract_keywords_from_instruction("PYTHON Async CODE")
        assert keywords == ["python", "async", "code"]

    def test_removes_duplicates(self):
        keywords = extract_keywords_from_instruction(
            "python is great and python is awesome"
        )
        assert keywords.count("python") == 1

    def test_regex_pattern_filters_non_word_chars(self):
        # Regex \b[a-zA-Z_]{3,}\b matches alphabetic words and underscores
        keywords = extract_keywords_from_instruction("hello_world foo bar")
        # "hello_world" matches as one token (underscores allowed in regex)
        assert "foo" in keywords
        assert "bar" in keywords

    def test_comprehensive_stopwords_filtering(self):
        instruction = (
            "the a an and or but in on at to for of with by from as is was "
            "are be been being have has had do does did will would could "
            "should may might must please help need want use make get"
        )
        keywords = extract_keywords_from_instruction(instruction)
        assert keywords == []

    def test_meaningful_words_kept(self):
        keywords = extract_keywords_from_instruction(
            "Implement calculator tool with arithmetic operations"
        )
        assert "implement" in keywords
        assert "calculator" in keywords
        assert "tool" in keywords
        assert "arithmetic" in keywords
        assert "operations" in keywords


class TestSelectRelevantHistory:
    """Tests for select_relevant_history function."""

    def make_delegation(self, instruction: str, summary: str) -> Delegation:
        model_config = _make_model()
        tuple_def = AgentTuple(
            instruction=instruction, context="", tools=[], model=model_config,
        )
        observation = Observation(result_summary=summary)
        cost_record = _make_cost_record()
        return Delegation(step=1, tuple=tuple_def, observation=observation, cost_record=cost_record)

    def test_empty_history_returns_empty_list(self):
        selected = select_relevant_history([], ["python"])
        assert selected == []

    def test_includes_recent_items(self):
        history = [
            self.make_delegation("task1", "result1"),
            self.make_delegation("task2", "result2"),
            self.make_delegation("task3", "result3"),
            self.make_delegation("task4", "result4"),
        ]
        selected = select_relevant_history(history, keywords=[], include_recent=2)
        assert len(selected) <= 5  # max_items default
        # Recent items should be included
        summaries = [s.observation.result_summary for s in selected]
        assert "result3" in summaries
        assert "result4" in summaries

    def test_scores_by_keyword_relevance(self):
        history = [
            self.make_delegation("task1", "python code"),
            self.make_delegation("task2", "javascript code"),
            self.make_delegation("task3", "python async"),
        ]
        selected = select_relevant_history(
            history, keywords=["python"], max_items=3, include_recent=0,
        )
        summaries = [s.observation.result_summary for s in selected]
        # Python-related items should be first (higher score)
        assert summaries[0] in ["python code", "python async"]
        assert summaries[1] in ["python code", "python async"]

    def test_respects_max_items_limit(self):
        history = [
            self.make_delegation(f"task{i}", f"result{i}") for i in range(10)
        ]
        selected = select_relevant_history(
            history, keywords=["result"], max_items=3, include_recent=0,
        )
        assert len(selected) <= 3

    def test_include_recent_zero_with_no_keywords(self):
        history = [
            self.make_delegation("task1", "result1"),
            self.make_delegation("task2", "result2"),
            self.make_delegation("task3", "result3"),
        ]
        selected = select_relevant_history(
            history, keywords=[], max_items=10, include_recent=0,
        )
        # With no keywords, returns history[:max_items]
        assert len(selected) == 3

    def test_recent_items_plus_scored_items(self):
        history = [
            self.make_delegation("old task", "old result"),
            self.make_delegation("python task1", "python result1"),
            self.make_delegation("python task2", "python result2"),
            self.make_delegation("recent task", "recent result"),
        ]
        selected = select_relevant_history(
            history, keywords=["python"], max_items=3, include_recent=1,
        )
        assert len(selected) <= 3
        summaries = [s.observation.result_summary for s in selected]
        # Recent item should be included
        assert "recent result" in summaries

    def test_empty_keywords_returns_items(self):
        history = [
            self.make_delegation(f"task{i}", f"result{i}") for i in range(5)
        ]
        selected = select_relevant_history(
            history, keywords=[], max_items=3, include_recent=0,
        )
        assert len(selected) == 3


class TestBuildContextForSubtask:
    """Tests for build_context_for_subtask function."""

    def make_delegation(self, instruction: str, summary: str) -> Delegation:
        model_config = _make_model()
        tuple_def = AgentTuple(
            instruction=instruction, context="", tools=[], model=model_config,
        )
        observation = Observation(result_summary=summary)
        cost_record = _make_cost_record()
        return Delegation(step=1, tuple=tuple_def, observation=observation, cost_record=cost_record)

    def test_empty_inputs_returns_empty_string(self):
        context = build_context_for_subtask("", [], [], 3)
        assert context == ""

    def test_includes_action_context(self):
        context = build_context_for_subtask("This is context", [], [], 3)
        assert "This is context" in context

    def test_action_context_only(self):
        context = build_context_for_subtask("Action context", [], [], 3)
        assert context == "Action context"

    def test_includes_history_with_header(self):
        history = [self.make_delegation("task", "result")]
        context = build_context_for_subtask("", history, [], 3)
        assert "**Relevant Previous Work:**" in context
        assert "- result" in context

    def test_uses_select_relevant_history(self):
        history = [
            self.make_delegation("task1", "result1"),
            self.make_delegation("task2", "result2"),
            self.make_delegation("task3", "result3"),
            self.make_delegation("task4", "result4"),
            self.make_delegation("task5", "result5"),
        ]
        context = build_context_for_subtask("", history, [], max_history_items=2)
        # Should limit history items
        count = context.count("- result")
        assert count <= 2

    def test_passes_keywords_to_selection(self):
        history = [
            self.make_delegation("python task", "python result"),
            self.make_delegation("other task", "other result"),
        ]
        context = build_context_for_subtask("", history, ["python"], max_history_items=1)
        assert "result" in context

    def test_respects_max_history_items(self):
        history = [
            self.make_delegation(f"task{i}", f"result{i}") for i in range(5)
        ]
        context = build_context_for_subtask("", history, [], max_history_items=2)
        assert context.count("- result") <= 2

    def test_combines_action_context_and_history(self):
        history = [self.make_delegation("task", "result")]
        context = build_context_for_subtask("Action context", history, [], 3)
        assert "Action context" in context
        assert "**Relevant Previous Work:**" in context
        assert "- result" in context

    def test_formats_observations_as_bullets(self):
        history = [
            self.make_delegation("task1", "result1"),
            self.make_delegation("task2", "result2"),
        ]
        context = build_context_for_subtask("", history, [], 3)
        assert "- result1" in context or "- result2" in context

    def test_empty_history_with_action_context(self):
        context = build_context_for_subtask("Some context", [], [], 3)
        assert context == "Some context"
        assert "**Relevant Previous Work:**" not in context

    def test_no_matching_history_returns_action_context(self):
        history = [self.make_delegation("task", "result")]
        context = build_context_for_subtask("Context", history, ["nonexistent"], max_history_items=3)
        # Should at least have action context
        assert "Context" in context
