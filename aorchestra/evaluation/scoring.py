"""Scoring mechanisms for evaluation.

Item 005: Exact match and LLM-as-judge scoring functions.
"""

from typing import Optional
import re


def score_exact_match(
    actual: Optional[str],
    expected: Optional[str],
    *,
    case_sensitive: bool = False,
    ignore_whitespace: bool = True,
    substring: bool = False,
) -> float:
    """Score an answer using exact match with normalization options.

    Args:
        actual: The actual answer from the system
        expected: The expected answer
        case_sensitive: If False, convert both to lowercase for comparison
        ignore_whitespace: If True, collapse multiple whitespace and strip
        substring: If True, return 1.0 if expected is contained in actual

    Returns:
        1.0 for match, 0.0 for no match

    Examples:
        >>> score_exact_match("120", "120")
        1.0
        >>> score_exact_match("Hello World", "hello world", case_sensitive=False)
        1.0
        >>> score_exact_match("Hello World", "World", substring=True)
        1.0
    """
    # Handle None values
    if actual is None or expected is None:
        return 0.0

    # Normalize case
    if not case_sensitive:
        actual = actual.lower()
        expected = expected.lower()

    # Normalize whitespace
    if ignore_whitespace:
        actual = re.sub(r'\s+', ' ', actual).strip()
        expected = re.sub(r'\s+', ' ', expected).strip()

    # Substring matching
    if substring:
        return 1.0 if expected in actual else 0.0

    # Exact match
    return 1.0 if actual == expected else 0.0


def score_exact_match_with_tolerance(
    actual: Optional[str],
    expected: Optional[str],
    *,
    tolerance: float = 0.0,
) -> float:
    """Score a numeric answer with tolerance for floating point comparison.

    Args:
        actual: The actual answer as a string
        expected: The expected answer as a string
        tolerance: Maximum allowed difference between actual and expected

    Returns:
        1.0 if within tolerance, 0.0 otherwise

    Examples:
        >>> score_exact_match_with_tolerance("3.14159", "3.14", tolerance=0.01)
        1.0
        >>> score_exact_match_with_tolerance("100", "101", tolerance=2)
        1.0
    """
    # Handle None values
    if actual is None or expected is None:
        return 0.0

    # Try to parse as numbers
    try:
        actual_num = float(actual)
        expected_num = float(expected)
        return 1.0 if abs(actual_num - expected_num) <= tolerance else 0.0
    except (ValueError, TypeError):
        # If parsing fails, fall back to regular exact match
        return score_exact_match(actual, expected)


async def score_llm_judge(
    goal: str,
    answer: str,
    client,
    model: str = "glm-4.7",
) -> float:
    """Score an answer using LLM-as-judge.

    Uses an LLM to evaluate the quality of an answer on a scale from 0.0 to 1.0.
    The LLM is prompted to consider accuracy, completeness, and clarity.

    Args:
        goal: The original task goal/instruction
        answer: The answer to evaluate
        client: OpenAI client instance (async)
        model: Model name to use for evaluation (default: glm-4.7)

    Returns:
        Score from 0.0 to 1.0, or 0.5 on parse failure

    Examples:
        >>> client = AsyncOpenAI(...)
        >>> score = await score_llm_judge("What is 2+2?", "The answer is 4.", client)
        0.95
    """
    if not answer or not answer.strip():
        return 0.0

    prompt = f"""Evaluate the quality of this answer on a scale from 0.0 to 1.0.

Consider the following criteria:
- Accuracy: Is the answer factually correct?
- Completeness: Does the answer fully address the question?
- Clarity: Is the answer well-structured and understandable?

Task/Goal:
{goal}

Answer to evaluate:
{answer}

Respond with ONLY a single number between 0.0 and 1.0. Do not include any explanation or additional text."""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=20,
        )

        # Parse score from response
        score_text = response.choices[0].message.content.strip()
        score = float(score_text)

        # Clamp to [0.0, 1.0] range
        score = max(0.0, min(1.0, score))
        return score

    except (ValueError, AttributeError) as e:
        # Parse failure - return default score
        return 0.5
    except Exception as e:
        # Other errors - return default score
        return 0.5


async def score_llm_judge_with_details(
    goal: str,
    answer: str,
    client,
    model: str = "glm-4.7",
) -> tuple[float, str]:
    """Score an answer using LLM-as-judge and return reasoning.

    Similar to score_llm_judge but also returns the LLM's reasoning.

    Args:
        goal: The original task goal/instruction
        answer: The answer to evaluate
        client: OpenAI client instance (async)
        model: Model name to use for evaluation (default: glm-4.7)

    Returns:
        Tuple of (score, reasoning) where score is 0.0-1.0 and reasoning is a string

    Examples:
        >>> client = AsyncOpenAI(...)
        >>> score, reasoning = await score_llm_judge_with_details(
        ...     "What is 2+2?", "The answer is 4.", client
        ... )
        >>> print(f"Score: {score}, Reasoning: {reasoning}")
        Score: 0.95, Reasoning: The answer is accurate and complete...
    """
    if not answer or not answer.strip():
        return 0.0, "Empty answer provided."

    prompt = f"""Evaluate the quality of this answer on a scale from 0.0 to 1.0.

Consider the following criteria:
- Accuracy: Is the answer factually correct?
- Completeness: Does the answer fully address the question?
- Clarity: Is the answer well-structured and understandable?

Task/Goal:
{goal}

Answer to evaluate:
{answer}

Provide your evaluation in the following format:
SCORE: [your score from 0.0 to 1.0]
REASONING: [your brief reasoning]"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
        )

        # Parse score and reasoning
        content = response.choices[0].message.content.strip()

        # Extract score
        score_match = None
        for line in content.split('\n'):
            if line.upper().startswith('SCORE:'):
                try:
                    score = float(line.split(':', 1)[1].strip())
                    score = max(0.0, min(1.0, score))
                    score_match = score
                    break
                except (ValueError, IndexError):
                    pass

        # Extract reasoning (capture all content after REASONING: on the same line and subsequent lines)
        reasoning_match = ""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.upper().startswith('REASONING:'):
                reasoning_match = line.split(':', 1)[1].strip()
                # Add any subsequent lines
                if i + 1 < len(lines):
                    subsequent_lines = '\n'.join(lines[i + 1:])
                    reasoning_match += '\n' + subsequent_lines
                break

        if score_match is None:
            return 0.5, content

        return score_match, reasoning_match

    except Exception as e:
        # Error - return default score and error message
        return 0.5, f"Error during evaluation: {str(e)}"
