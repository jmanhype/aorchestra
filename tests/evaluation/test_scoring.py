"""Tests for evaluation scoring mechanisms."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from aorchestra.evaluation.scoring import (
    score_exact_match,
    score_exact_match_with_tolerance,
    score_llm_judge,
    score_llm_judge_with_details,
)


class TestScoreLLMJudge:
    """Tests for score_exact_match function."""

    def test_exact_match_simple(self):
        """Test simple exact match."""
        assert score_exact_match("120", "120") == 1.0
        assert score_exact_match("hello", "world") == 0.0

    def test_case_insensitive_default(self):
        """Test default case insensitive matching."""
        assert score_exact_match("Hello", "hello") == 1.0
        assert score_exact_match("HELLO", "hello") == 1.0
        assert score_exact_match("Hello World", "hello world") == 1.0

    def test_case_sensitive(self):
        """Test case sensitive matching."""
        assert score_exact_match("Hello", "hello", case_sensitive=True) == 0.0
        assert score_exact_match("Hello", "Hello", case_sensitive=True) == 1.0

    def test_ignore_whitespace_default(self):
        """Test default whitespace normalization."""
        assert score_exact_match("hello  world", "hello world") == 1.0
        assert score_exact_match("  hello  world  ", "hello world") == 1.0
        assert score_exact_match("\thello\nworld", "hello world") == 1.0

    def test_preserve_whitespace(self):
        """Test preserving whitespace."""
        assert score_exact_match("hello  world", "hello world", ignore_whitespace=False) == 0.0
        assert score_exact_match("hello  world", "hello  world", ignore_whitespace=False) == 1.0

    def test_none_values(self):
        """Test handling of None values."""
        assert score_exact_match(None, "120") == 0.0
        assert score_exact_match("120", None) == 0.0
        assert score_exact_match(None, None) == 0.0

    def test_empty_strings(self):
        """Test handling of empty strings."""
        assert score_exact_match("", "") == 1.0
        assert score_exact_match("", "hello") == 0.0
        assert score_exact_match("hello", "") == 0.0

    def test_substring_matching(self):
        """Test substring matching."""
        assert score_exact_match("Hello World", "World", substring=True) == 1.0
        assert score_exact_match("Hello World", "Hello", substring=True) == 1.0
        assert score_exact_match("Hello World", "lo Wo", substring=True) == 1.0
        assert score_exact_match("Hello World", "Goodbye", substring=True) == 0.0

    def test_substring_case_insensitive(self):
        """Test substring matching with case insensitivity."""
        assert score_exact_match("Hello World", "world", substring=True) == 1.0
        assert score_exact_match("Hello World", "WORLD", substring=True) == 1.0

    def test_combined_options(self):
        """Test combined normalization options."""
        assert score_exact_match("  HELLO  WORLD  ", "hello world", case_sensitive=False, ignore_whitespace=True) == 1.0
        assert score_exact_match("HELLO WORLD", "hello", case_sensitive=False, substring=True) == 1.0


class TestScoreExactMatchWithTolerance:
    """Tests for score_exact_match_with_tolerance function."""

    def test_exact_match_numbers(self):
        """Test exact numeric match."""
        assert score_exact_match_with_tolerance("120", "120") == 1.0
        assert score_exact_match_with_tolerance("120.5", "120.5") == 1.0

    def test_tolerance_simple(self):
        """Test simple tolerance."""
        assert score_exact_match_with_tolerance("102", "100", tolerance=2) == 1.0
        assert score_exact_match_with_tolerance("102", "100", tolerance=1) == 0.0

    def test_tolerance_floating_point(self):
        """Test tolerance with floating point numbers."""
        assert score_exact_match_with_tolerance("3.14159", "3.14", tolerance=0.01) == 1.0
        assert score_exact_match_with_tolerance("3.14159", "3.14", tolerance=0.001) == 0.0

    def test_tolerance_negative_numbers(self):
        """Test tolerance with negative numbers."""
        assert score_exact_match_with_tolerance("-5.5", "-5.0", tolerance=0.5) == 1.0
        assert score_exact_match_with_tolerance("-5.5", "-5.0", tolerance=0.4) == 0.0

    def test_non_numeric_fallback(self):
        """Test fallback to exact match for non-numeric strings."""
        assert score_exact_match_with_tolerance("Hello World", "Hello World") == 1.0
        assert score_exact_match_with_tolerance("Hello World", "Goodbye") == 0.0

    def test_none_values(self):
        """Test handling of None values."""
        assert score_exact_match_with_tolerance(None, "120") == 0.0
        assert score_exact_match_with_tolerance("120", None) == 0.0
        assert score_exact_match_with_tolerance(None, None) == 0.0

    def test_zero_tolerance(self):
        """Test zero tolerance (exact match required)."""
        assert score_exact_match_with_tolerance("100", "100", tolerance=0) == 1.0
        assert score_exact_match_with_tolerance("100.001", "100", tolerance=0) == 0.0

    def test_integer_string_parsing(self):
        """Test parsing of integer strings."""
        assert score_exact_match_with_tolerance("42", "42.0", tolerance=0) == 1.0
        assert score_exact_match_with_tolerance("42", "42.5", tolerance=0) == 0.0

    def test_large_tolerance(self):
        """Test large tolerance values."""
        assert score_exact_match_with_tolerance("1000", "500", tolerance=500) == 1.0
        assert score_exact_match_with_tolerance("1000", "2000", tolerance=1000) == 1.0


class TestScoreLLMJudge:
    """Tests for score_llm_judge function."""

    @pytest.mark.asyncio
    async def test_score_llm_judge_parses_float(self):
        """Test that score_llm_judge parses float from LLM response."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "0.85"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score = await score_llm_judge(
                goal="What is 2+2?",
                answer="The answer is 4.",
                client=mock_client,
            )

            assert score == 0.85

            # Verify the call
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["max_tokens"] == 20

    @pytest.mark.asyncio
    async def test_score_llm_judge_clamps_to_range(self):
        """Test that score_llm_judge clamps to [0.0, 1.0] range."""
        mock_client = Mock()

        # Test upper clamp
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "1.5"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score = await score_llm_judge(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 1.0

        # Test lower clamp
        mock_response.choices[0].message.content = "-0.5"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score = await score_llm_judge(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_llm_judge_parse_failure_returns_default(self):
        """Test that score_llm_judge returns 0.5 on parse failure."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "not a number"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score = await score_llm_judge(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 0.5

    @pytest.mark.asyncio
    async def test_score_llm_judge_empty_answer_returns_zero(self):
        """Test that empty answers return 0.0 without calling LLM."""
        mock_client = Mock()

        score = await score_llm_judge(
            goal="Test",
            answer="",
            client=mock_client,
        )
        assert score == 0.0

        score = await score_llm_judge(
            goal="Test",
            answer="   ",
            client=mock_client,
        )
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_score_llm_judge_api_error_returns_default(self):
        """Test that API errors return 0.5."""
        mock_client = Mock()

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API error")

            score = await score_llm_judge(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 0.5

    @pytest.mark.asyncio
    async def test_score_llm_judge_various_scores(self):
        """Test various score values."""
        mock_client = Mock()

        test_cases = [0.0, 0.25, 0.5, 0.75, 1.0]

        for expected_score in test_cases:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = str(expected_score)

            with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_response

                score = await score_llm_judge(
                    goal="Test",
                    answer="Test answer",
                    client=mock_client,
                )
                assert score == expected_score

    @pytest.mark.asyncio
    async def test_score_llm_judge_custom_model(self):
        """Test that custom model parameter works."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "0.75"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score = await score_llm_judge(
                goal="Test",
                answer="Test answer",
                client=mock_client,
                model="custom-model",
            )

            # Verify custom model was used
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "custom-model"


class TestScoreLLMJudgeWithDetails:
    """Tests for score_llm_judge_with_details function."""

    @pytest.mark.asyncio
    async def test_returns_score_and_reasoning(self):
        """Test that function returns both score and reasoning."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SCORE: 0.85\nREASONING: The answer is accurate."

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, reasoning = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )

            assert score == 0.85
            assert reasoning == "The answer is accurate."

    @pytest.mark.asyncio
    async def test_parse_failure_returns_default(self):
        """Test that parse failure returns default score."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "No score found"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, reasoning = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )

            assert score == 0.5
            assert reasoning == "No score found"

    @pytest.mark.asyncio
    async def test_clamps_score_to_range(self):
        """Test that score is clamped to [0.0, 1.0]."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]

        # Test upper clamp
        mock_response.choices[0].message.content = "SCORE: 1.5\nREASONING: Test"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, _ = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 1.0

        # Test lower clamp
        mock_response.choices[0].message.content = "SCORE: -0.5\nREASONING: Test"

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, _ = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )
            assert score == 0.0

    @pytest.mark.asyncio
    async def test_empty_answer(self):
        """Test that empty answer returns zero score."""
        mock_client = Mock()

        score, reasoning = await score_llm_judge_with_details(
            goal="Test",
            answer="",
            client=mock_client,
        )

        assert score == 0.0
        assert reasoning == "Empty answer provided."

    @pytest.mark.asyncio
    async def test_api_error(self):
        """Test that API errors return default score."""
        mock_client = Mock()

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API error")

            score, reasoning = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )

            assert score == 0.5
            assert "Error during evaluation" in reasoning

    @pytest.mark.asyncio
    async def test_multiline_reasoning(self):
        """Test that multiline reasoning is handled correctly."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SCORE: 0.75\nREASONING: The answer is accurate.\nIt is also complete."

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, reasoning = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )

            assert score == 0.75
            assert reasoning == "The answer is accurate.\nIt is also complete."

    @pytest.mark.asyncio
    async def test_case_insensitive_keywords(self):
        """Test that SCORE and REASONING are case insensitive."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]

        # Test lowercase
        mock_response.choices[0].message.content = "score: 0.8\nreasoning: Good answer."

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            score, reasoning = await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
            )

            assert score == 0.8
            assert reasoning == "Good answer."

    @pytest.mark.asyncio
    async def test_custom_model(self):
        """Test that custom model parameter works."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SCORE: 0.9\nREASONING: Excellent."

        with patch.object(mock_client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response

            await score_llm_judge_with_details(
                goal="Test",
                answer="Test answer",
                client=mock_client,
                model="custom-model",
            )

            # Verify custom model was used
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "custom-model"
