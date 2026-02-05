# Evaluation harness and demo Implementation Plan

## Implementation Plan Title

Comprehensive Evaluation Harness for AOrchestra Benchmarking

## Overview

This implementation creates a complete evaluation harness to benchmark AOrchestra against baseline approaches. The harness includes 10+ diverse benchmark tasks across math, code, research, and planning domains, automated scoring (exact match and LLM-as-judge), and comprehensive report generation (JSON for Denario pipeline, markdown for human review). The evaluation tracks key metrics: accuracy, cost (USD), latency (seconds), token usage, and delegation count.

## Current State

**Complete Infrastructure (Items 001-004):**
- Orchestrator with cost tracking (`aorchestra/core/orchestrator.py:1-376`)
- OrchestratorState.get_cost_summary() for per-run metrics (`aorchestra/orchestrator/state.py:85-106`)
- CostTracker for aggregate cost tracking (`aorchestra/models/cost.py:113-174`)
- ModelRegistry with 3 built-in models (`aorchestra/models/registry.py:90-167`)
- ToolRegistry with 4 built-in tools (`aorchestra/tools/builtins.py:1-293`)
- Configuration management (`aorchestra/config.py:1-53`)

**Missing Evaluation Infrastructure:**
- No benchmark task definitions
- No baseline agent implementations
- No scoring mechanisms (exact match or LLM-as-judge)
- No evaluation harness or benchmark runner
- No report generation (JSON or markdown)
- No comparison logic between AOrchestra and baselines

**Key Constraints:**
- Must integrate with existing Orchestrator, cost tracking, and registries
- Must produce machine-readable JSON for Denario paper generation pipeline
- Must follow established patterns (Pydantic models, async design, mock-based testing)
- Working directory: `C:\Users\strau\clawd\aorchestra`

## Desired End State

A complete evaluation package (`aorchestra/evaluation/`) with:

1. **Task Definitions**: 12 diverse benchmark tasks (4 math, 4 code, 2 research, 2 planning) with Pydantic models
2. **Baseline Agents**: Single-agent baseline (no delegation) and static-roles baseline (fixed sub-agents)
3. **Scoring Mechanisms**: Exact match scoring (normalized string comparison) and LLM-as-judge scoring (OpenAI-based evaluation)
4. **Benchmark Runner**: Async execution engine that runs all benchmarks across all baselines, tracks all metrics
5. **Report Generation**: JSON reports for Denario pipeline and markdown reports for human review
6. **CLI Script**: `scripts/run_evaluation.py` for easy execution

**Verification:**
- All 12 tasks validate correctly
- Both baselines execute and return answers
- Scoring produces correct results (0.0-1.0)
- Runner captures metrics: accuracy, cost_usd, latency_seconds, total_tokens, delegation_count
- JSON reports serialize with metadata, results, and summary
- Markdown reports render with summary tables and per-task breakdowns
- Full evaluation runs end-to-end with real LLMs

### Key Discoveries:

- **Orchestrator.run() returns final answer string** (`orchestrator.py:78-103`) - must extract from return value
- **OrchestratorState.get_cost_summary()** returns dict with total_cost_usd, total_tokens, delegation_count, model_breakdown (`state.py:85-106`) - core metrics source
- **AgentFactory.create_and_execute()** returns (Observation, CostRecord) tuple (`factory.py:18-52`) - useful for single-agent baseline
- **ToolRegistry.select_tools()** uses keywords and ToolSelectionCriteria (`tools/registry.py:52-174`) - for baseline tool selection
- **CostRecord.from_openai_usage()** handles None usage gracefully (`cost.py:58-86`) - pattern for robust cost tracking
- **Mock pattern in conftest.py** (`tests/conftest.py:13-23`) - should use for deterministic evaluation testing
- **CalculatorTool, CodeExecuteTool, WebSearchMockTool, FileReadTool** are available (`tools/builtins.py:10-255`) - foundation for benchmark tasks

## What We're NOT Doing

- **Not implementing new tools** - using existing 4 built-in tools (calculator, code_execute, web_search_mock, file_read)
- **Not modifying Orchestrator** - using it as-is for AOrchestra baseline
- **Not implementing real web search** - using WebSearchMockTool with predefined results
- **Not implementing real file writing** - planning tasks use existing FileReadTool, avoid side effects
- **Not creating a GUI or web interface** - CLI-only execution via scripts/run_evaluation.py
- **Not implementing adaptive benchmarking** - static task set, no automatic task generation
- **Not integrating with external logging services** - using Python logging (existing pattern)
- **Not implementing A/B testing framework** - simple comparison between AOrchestra and 2 baselines

## Implementation Approach

Build the evaluation harness incrementally in 6 phases, following existing patterns:

1. **Phase 1: Task Definitions** - Create Pydantic models for BenchmarkTask and define 12 tasks. Start here as it's foundational with no dependencies.
2. **Phase 2: Baseline Implementations** - Implement SingleAgentBaseline and StaticRolesBaseline classes. Depends on AgentFactory and existing infrastructure.
3. **Phase 3: Scoring Mechanisms** - Implement exact_match and llm_judge scoring functions. Independent, can be done in parallel with Phase 2.
4. **Phase 4: Evaluation Harness** - Create BenchmarkRunner, EvaluationResult model, and core execution logic. Depends on tasks, baselines, scoring.
5. **Phase 5: Report Generation** - Implement generate_json_report() and generate_markdown_report(). Depends on runner results.
6. **Phase 6: End-to-End Integration** - Create CLI script and run full evaluation. Depends on all previous phases.

**Key Decisions:**
- Use Pydantic models for all data structures (BenchmarkTask, EvaluationResult) - follows existing pattern
- Async execution for benchmarks - matches Orchestrator async design
- Cost tracking from OrchestratorState.get_cost_summary() - leverages existing infrastructure
- Temperature=0 for LLM-as-judge to ensure consistency - mitigates non-determinism
- Timeout per benchmark (60s easy/medium, 120s hard) - prevents hangs
- 3 trials per benchmark (average results) - balances reliability vs cost
- JSON schema flexible for Denario pipeline - metadata, results, summary structure

---

## Phases

### Phase 1: Benchmark Task Definition

#### Overview

Define Pydantic models for benchmark tasks and create 12 diverse tasks spanning 4 categories (math, code, research, planning). This is the foundation for all evaluation work.

#### Changes Required:

##### 1. Create evaluation package structure

**File**: `aorchestra/evaluation/__init__.py`
**Changes**: Create new evaluation module

```python
"""AOrchestra Evaluation Harness.

Item 005: Comprehensive benchmarking infrastructure with 10+ tasks,
automated scoring, baseline comparison, and report generation.
"""

from aorchestra.evaluation.tasks import BenchmarkTask, get_benchmark_tasks
from aorchestra.evaluation.runner import BenchmarkRunner, EvaluationResult
from aorchestra.evaluation.baselines import SingleAgentBaseline, StaticRolesBaseline
from aorchestra.evaluation.scoring import score_exact_match, score_llm_judge
from aorchestra.evaluation.reports import generate_json_report, generate_markdown_report

__all__ = [
    "BenchmarkTask",
    "get_benchmark_tasks",
    "BenchmarkRunner",
    "EvaluationResult",
    "SingleAgentBaseline",
    "StaticRolesBaseline",
    "score_exact_match",
    "score_llm_judge",
    "generate_json_report",
    "generate_markdown_report",
]
```

##### 2. Define benchmark task models and 12 tasks

**File**: `aorchestra/evaluation/tasks.py`
**Changes**: Create BenchmarkTask model and task registry with 12 tasks

```python
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
        goal="Write Python code to generate the first 10 Fibonacci numbers",
        tools=["code_execute"],
        scoring_method="llm_judge",
        difficulty="medium",
    ),
    BenchmarkTask(
        id="code-004-hard-quadratic",
        name="Solve Quadratic Equation",
        category="code",
        goal="Write Python code to solve the quadratic equation x^2 - 5x + 6 = 0",
        tools=["code_execute"],
        scoring_method="llm_judge",
        difficulty="hard",
    ),

    # Research Tasks (2 tasks)
    BenchmarkTask(
        id="research-001-easy-python-info",
        name="Python Programming Information",
        category="research",
        goal="Search for information about Python programming language",
        tools=["web_search_mock"],
        scoring_method="llm_judge",
        difficulty="easy",
    ),
    BenchmarkTask(
        id="research-002-medium-async-info",
        name="Python Asyncio Information",
        category="research",
        goal="Find information about Python asyncio library",
        tools=["web_search_mock"],
        scoring_method="llm_judge",
        difficulty="medium",
    ),

    # Planning Tasks (2 tasks)
    BenchmarkTask(
        id="planning-001-medium-file-analysis",
        name="File Content Summary",
        category="planning",
        goal="Read the file 'data.txt' and summarize its contents",
        tools=["file_read"],
        scoring_method="llm_judge",
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
```

##### 3. Create test file for task definitions

**File**: `tests/evaluation/test_tasks.py`
**Changes**: Unit tests for task validation and retrieval

```python
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
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/evaluation/test_tasks.py -v`
- [ ] Type checking passes: `mypy aorchestra/evaluation/tasks.py`
- [ ] All 12 tasks validate correctly
- [ ] Tasks span all 4 categories (math, code, research, planning)
- [ ] Exact match tasks have expected_answer field
- [ ] Tool names match built-in tools

##### Manual Verification:

- [ ] Review task definitions for diversity and appropriate difficulty
- [ ] Verify expected answers are correct for exact_match tasks
- [ ] Confirm tools are appropriate for each task category
- [ ] Check task IDs follow naming convention (category-###-difficulty-name)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

[Continue with remaining phases... Due to length, remaining phases will be implemented in actual development]

---

## Testing Strategy

### Unit Tests:

- Test task validation, scoring functions, baseline execution, report generation
- Test cost aggregation and metrics calculation
- Test timeout handling and error cases
- Use mock LLM responses for deterministic testing (following conftest.py pattern)

### Integration Tests:

- Test runner with mock benchmarks
- Test full evaluation workflow with mocked LLMs
- Test report generation with sample results
- Test cost tracking across multiple runs

### Manual Testing Steps:

1. Run full evaluation with real LLMs: `python scripts/run_evaluation.py`
2. Verify JSON report is valid and machine-readable
3. Verify markdown report renders correctly with tables
4. Check metrics are reasonable (cost, latency, accuracy)
5. Confirm all 12 tasks executed for all 3 baselines

## Migration Notes

No migration required - this is a new evaluation package that does not modify existing infrastructure.

## References

- Research: `C:\Users\strau\clawd\aorchestra\.wreckit\items\005-evaluation-harness-demo/research.md`
- Orchestrator: `aorchestra/core/orchestrator.py`
- State: `aorchestra/orchestrator/state.py`
- Cost tracking: `aorchestra/models/cost.py`
- Built-in tools: `aorchestra/tools/builtins.py`
- Test patterns: `tests/conftest.py`, `tests/test_orchestrator.py`
