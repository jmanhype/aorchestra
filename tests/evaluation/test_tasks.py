"""Tests for evaluation task definitions."""

import pytest
from aorchestra.evaluation.tasks import (
    BenchmarkTask,
    get_benchmark_tasks,
    get_task_by_id,
    get_tasks_by_category,
    get_tasks_by_difficulty,
)


def test_get_benchmark_tasks_returns_12_tasks():
    """Test that get_benchmark_tasks returns 12 tasks."""
    tasks = get_benchmark_tasks()
    assert len(tasks) == 12


def test_all_tasks_validate_correctly():
    """Test that all tasks are valid Pydantic models."""
    tasks = get_benchmark_tasks()
    for task in tasks:
        assert isinstance(task, BenchmarkTask)
        assert task.id  # ID required
        assert task.name  # Name required
        assert task.goal  # Goal required
        assert task.category in ["math", "code", "research", "planning"]
        assert task.scoring_method in ["exact_match", "llm_judge"]
        assert task.difficulty in ["easy", "medium", "hard"]


def test_tasks_span_4_categories():
    """Test that tasks span all 4 required categories."""
    tasks = get_benchmark_tasks()
    categories = {task.category for task in tasks}
    assert categories == {"math", "code", "research", "planning"}


def test_math_tasks_count():
    """Test that there are 4 math tasks."""
    math_tasks = get_tasks_by_category("math")
    assert len(math_tasks) == 4


def test_code_tasks_count():
    """Test that there are 4 code tasks."""
    code_tasks = get_tasks_by_category("code")
    assert len(code_tasks) == 4


def test_research_tasks_count():
    """Test that there are 2 research tasks."""
    research_tasks = get_tasks_by_category("research")
    assert len(research_tasks) == 2


def test_planning_tasks_count():
    """Test that there are 2 planning tasks."""
    planning_tasks = get_tasks_by_category("planning")
    assert len(planning_tasks) == 2


def test_exact_match_tasks_have_expected_answer():
    """Test that exact_match tasks have expected_answer."""
    tasks = get_benchmark_tasks()
    for task in tasks:
        if task.scoring_method == "exact_match":
            assert task.expected_answer is not None


def test_get_task_by_id():
    """Test getting task by ID."""
    task = get_task_by_id("math-001-easy-addition")
    assert task.id == "math-001-easy-addition"
    assert task.category == "math"
    assert task.difficulty == "easy"


def test_get_task_by_id_not_found():
    """Test that get_task_by_id raises KeyError for unknown ID."""
    with pytest.raises(KeyError):
        get_task_by_id("unknown-task-id")


def test_difficulty_distribution():
    """Test that tasks span all difficulty levels."""
    tasks = get_benchmark_tasks()
    difficulties = {task.difficulty for task in tasks}
    assert difficulties == {"easy", "medium", "hard"}


def test_tool_names_are_valid():
    """Test that task tool names are from built-in tools."""
    tasks = get_benchmark_tasks()
    valid_tools = {"calculator", "code_execute", "web_search_mock", "file_read"}
    for task in tasks:
        for tool_name in task.tools:
            assert tool_name in valid_tools
