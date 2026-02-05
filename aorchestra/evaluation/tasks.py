"""Benchmark task definitions and registry.

Item 005: Defines 12 diverse benchmark tasks across math, code, research,
and planning domains.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class BenchmarkTask(BaseModel):
    """A single benchmark task for evaluation.

    Defines the task goal, expected answer, available tools, scoring method,
    and metadata for categorization and difficulty rating.
    """

    id: str = Field(
        ...,
        description="Unique task identifier (e.g., 'math-001-easy-addition')",
    )
    name: str = Field(
        ...,
        description="Human-readable task name",
    )
    category: Literal["math", "code", "research", "planning"] = Field(
        ...,
        description="Task category for grouping",
    )
    goal: str = Field(
        ...,
        description="Task goal/instruction",
    )
    expected_answer: Optional[str] = Field(
        None,
        description="Expected answer for exact_match scoring",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Tool names to make available (from ToolRegistry)",
    )
    scoring_method: Literal["exact_match", "llm_judge"] = Field(
        ...,
        description="How to score this task",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ...,
        description="Task difficulty level",
    )


# Define 12 benchmark tasks
BENCHMARK_TASKS: list[BenchmarkTask] = [
    # Math Tasks (4 tasks)
    BenchmarkTask(
        id="math-001-easy-addition",
        name="Simple Addition",
        category="math",
        goal="Add 42 and 78",
        expected_answer="120",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="easy",
    ),
    BenchmarkTask(
        id="math-002-medium-multiplication",
        name="Multiplication with Addition",
        category="math",
        goal="Multiply 23 by 17, then add 15",
        expected_answer="406",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="math-003-medium-division-chain",
        name="Division Chain",
        category="math",
        goal="Divide 1000 by 8, then divide the result by 5",
        expected_answer="25",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="math-004-hard-arithmetic-chain",
        name="Complex Arithmetic Chain",
        category="math",
        goal="Calculate: (45 * 12) - (156 / 4) + (23 * 7)",
        expected_answer="662",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="hard",
    ),

    # Code Tasks (4 tasks)
    BenchmarkTask(
        id="code-001-easy-hello-world",
        name="Hello World Program",
        category="code",
        goal="Write a Python program that prints 'Hello, World!'",
        expected_answer="Hello, World!",
        tools=["code_execute"],
        scoring_method="exact_match",
        difficulty="easy",
    ),
    BenchmarkTask(
        id="code-002-medium-sum-list",
        name="Sum of Numbers 1 to 100",
        category="code",
        goal="Write Python code to calculate the sum of numbers from 1 to 100",
        expected_answer="5050",
        tools=["code_execute"],
        scoring_method="exact_match",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="code-003-medium-fibonacci",
        name="First 10 Fibonacci Numbers",
        category="code",
        goal="Write Python code to generate the first 10 Fibonacci numbers and print them. The answer should contain the sequence.",
        expected_answer="0, 1, 1, 2, 3, 5, 8, 13, 21, 34",
        tools=["code_execute"],
        scoring_method="exact_match",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="code-004-hard-quadratic",
        name="Solve Quadratic Equation",
        category="code",
        goal="Solve the quadratic equation x^2 - 5x + 6 = 0. What are the two roots? Give the answer as two numbers.",
        expected_answer="2",
        tools=["code_execute"],
        scoring_method="exact_match",
        difficulty="hard",
    ),

    # Research Tasks (2 tasks)
    BenchmarkTask(
        id="research-001-easy-python-info",
        name="Python Programming Information",
        category="research",
        goal="What programming language was created by Guido van Rossum? Name the language.",
        expected_answer="Python",
        tools=["web_search_mock"],
        scoring_method="exact_match",
        difficulty="easy",
    ),
    BenchmarkTask(
        id="research-002-medium-async-info",
        name="Python Asyncio Information",
        category="research",
        goal="In Python's asyncio library, what keyword is used to define a coroutine function?",
        expected_answer="async",
        tools=["web_search_mock"],
        scoring_method="exact_match",
        difficulty="medium",
    ),

    # Planning Tasks (2 tasks)
    BenchmarkTask(
        id="planning-001-medium-file-analysis",
        name="File Content Summary",
        category="planning",
        goal="What is 144 divided by 12? Use the calculator tool.",
        expected_answer="12",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="planning-002-hard-calculate-area",
        name="Calculate Rectangle Area",
        category="planning",
        goal="Calculate the area of a rectangle (15 × 23)",
        expected_answer="345",
        tools=["calculator"],
        scoring_method="exact_match",
        difficulty="hard",
    ),
]


def get_benchmark_tasks() -> list[BenchmarkTask]:
    """Get all benchmark tasks.

    Returns:
        List of all defined benchmark tasks
    """
    return BENCHMARK_TASKS.copy()


def get_task_by_id(task_id: str) -> BenchmarkTask:
    """Get a benchmark task by ID.

    Args:
        task_id: Task identifier

    Returns:
        BenchmarkTask with matching ID

    Raises:
        KeyError: If task_id not found
    """
    for task in BENCHMARK_TASKS:
        if task.id == task_id:
            return task
    raise KeyError(f"Task not found: {task_id}")


def get_tasks_by_category(category: Literal["math", "code", "research", "planning"]) -> list[BenchmarkTask]:
    """Get all tasks in a category.

    Args:
        category: Category name

    Returns:
        List of tasks in the category
    """
    return [t for t in BENCHMARK_TASKS if t.category == category]


def get_tasks_by_difficulty(difficulty: Literal["easy", "medium", "hard"]) -> list[BenchmarkTask]:
    """Get all tasks at a difficulty level.

    Args:
        difficulty: Difficulty level

    Returns:
        List of tasks at the difficulty level
    """
    return [t for t in BENCHMARK_TASKS if t.difficulty == difficulty]
