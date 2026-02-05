"""Benchmark runner and evaluation result models.

Item 005: Core evaluation harness for running benchmarks.
"""

import asyncio
import time
from datetime import datetime
from typing import Literal, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from aorchestra.core.orchestrator import Orchestrator
from aorchestra.evaluation.tasks import BenchmarkTask
from aorchestra.evaluation.baselines import SingleAgentBaseline, StaticRolesBaseline
from aorchestra.evaluation.scoring import score_exact_match, score_llm_judge
from aorchestra.models.config import ModelConfig
from aorchestra.tools.registry import ToolRegistry


class EvaluationResult(BaseModel):
    """Result from running a single benchmark task with a single system."""

    task_id: str = Field(..., description="Task identifier")
    task_name: str = Field(..., description="Task name")
    task_category: Literal["math", "code", "research", "planning"] = Field(
        ..., description="Task category"
    )
    task_difficulty: Literal["easy", "medium", "hard"] = Field(
        ..., description="Task difficulty"
    )
    system: Literal["aorchestra", "single_agent", "static_roles"] = Field(
        ..., description="System that solved the task"
    )
    answer: str = Field(..., description="Answer from the system")
    score: float = Field(..., description="Score 0.0-1.0", ge=0.0, le=1.0)
    cost_usd: float = Field(..., description="Cost in USD", ge=0.0)
    latency_seconds: float = Field(..., description="Latency in seconds", ge=0.0)
    total_tokens: int = Field(..., description="Total tokens used", ge=0)
    delegation_count: int = Field(..., description="Number of delegations", ge=0)
    model_breakdown: dict = Field(
        default_factory=dict, description="Cost and token breakdown by model"
    )
    error: Optional[str] = Field(None, description="Error message if task failed")
    timestamp: str = Field(..., description="ISO timestamp of result")

    class Config:
        protected_namespaces = ()


class BenchmarkRunner:
    """Benchmark runner for executing tasks across multiple systems.

    Runs all benchmark tasks for AOrchestra and baseline systems (single_agent,
    static_roles), tracks metrics, and applies scoring.
    """

    def __init__(
        self,
        tasks: list[BenchmarkTask],
        model: ModelConfig,
        tool_registry: ToolRegistry,
        lambda_param: float = 0.5,
        num_trials: int = 1,
        timeouts: dict[str, int] = None,
    ):
        """Initialize the benchmark runner.

        Args:
            tasks: List of benchmark tasks to run
            model: Model configuration for all systems
            tool_registry: Tool registry for tool access
            lambda_param: Cost-performance trade-off for Orchestrator
            num_trials: Number of trials per task (results averaged)
            timeouts: Timeout per task by difficulty {"easy": 60, "medium": 90, "hard": 120}
        """
        self.tasks = tasks
        self.model = model
        self.tool_registry = tool_registry
        self.lambda_param = lambda_param
        self.num_trials = num_trials

        # Default timeouts by difficulty
        self.timeouts = timeouts or {
            "easy": 60,
            "medium": 90,
            "hard": 120,
        }

        # Initialize systems
        self.orchestrator = None  # Will be created per trial
        self.single_agent = SingleAgentBaseline(model, tool_registry)
        self.static_roles = StaticRolesBaseline(model, tool_registry)

        # LLM client for scoring
        self.client = AsyncOpenAI(
            api_key=model.api_key or "dummy",
            base_url=model.api_base,
        )

        # Results storage
        self.results: dict[str, list[EvaluationResult]] = {
            "aorchestra": [],
            "single_agent": [],
            "static_roles": [],
        }

    async def _run_aorchestra(
        self,
        task: BenchmarkTask,
        timeout: int,
    ) -> tuple[str, dict]:
        """Run task using AOrchestra Orchestrator.

        Args:
            task: Benchmark task to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (answer, metrics_dict)
        """
        # Create orchestrator for this trial
        orchestrator = Orchestrator(
            model_name=self.model.name,
            api_key=self.model.api_key,
            api_base=self.model.api_base,
            tool_registry=self.tool_registry,
            lambda_param=self.lambda_param,
            max_steps=10,
        )

        # Get tools for this task
        tools = [self.tool_registry.get(tool_name) for tool_name in task.tools]
        tools = [t for t in tools if t is not None]

        # Run orchestrator
        answer = await orchestrator.run(task.goal)

        # Extract metrics from state
        cost_summary = orchestrator.state.get_cost_summary()

        metrics = {
            "cost_usd": cost_summary["total_cost_usd"],
            "total_tokens": cost_summary["total_tokens"],
            "delegation_count": cost_summary["delegation_count"],
            "model_breakdown": cost_summary.get("model_breakdown", {}),
        }

        return answer, metrics

    async def _run_single_agent(
        self,
        task: BenchmarkTask,
        timeout: int,
    ) -> tuple[str, dict]:
        """Run task using SingleAgentBaseline.

        Args:
            task: Benchmark task to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (answer, metrics_dict)
        """
        answer, cost_record = await asyncio.wait_for(
            self.single_agent.solve(
                goal=task.goal,
                tool_names=task.tools,
                context="",
            ),
            timeout=timeout,
        )

        metrics = {
            "cost_usd": cost_record.estimated_cost_usd,
            "total_tokens": cost_record.total_tokens,
            "delegation_count": 0,  # Single agent has no delegation
            "model_breakdown": {
                cost_record.model_name: {
                    "cost_usd": cost_record.estimated_cost_usd,
                    "prompt_tokens": cost_record.prompt_tokens,
                    "completion_tokens": cost_record.completion_tokens,
                    "total_tokens": cost_record.total_tokens,
                }
            },
        }

        return answer, metrics

    async def _run_static_roles(
        self,
        task: BenchmarkTask,
        timeout: int,
    ) -> tuple[str, dict]:
        """Run task using StaticRolesBaseline.

        Args:
            task: Benchmark task to run
            timeout: Timeout in seconds

        Returns:
            Tuple of (answer, metrics_dict)
        """
        answer, cost_record = await asyncio.wait_for(
            self.static_roles.solve(
                goal=task.goal,
                tool_names=task.tools,
                context="",
            ),
            timeout=timeout,
        )

        metrics = {
            "cost_usd": cost_record.estimated_cost_usd,
            "total_tokens": cost_record.total_tokens,
            "delegation_count": 0,  # Static roles has no delegation (single selected agent)
            "model_breakdown": {
                cost_record.model_name: {
                    "cost_usd": cost_record.estimated_cost_usd,
                    "prompt_tokens": cost_record.prompt_tokens,
                    "completion_tokens": cost_record.completion_tokens,
                    "total_tokens": cost_record.total_tokens,
                }
            },
        }

        return answer, metrics

    async def _run_benchmark(
        self,
        task: BenchmarkTask,
        system: Literal["aorchestra", "single_agent", "static_roles"],
    ) -> EvaluationResult:
        """Run a single benchmark task for a single system.

        Args:
            task: Benchmark task to run
            system: System to use

        Returns:
            EvaluationResult with metrics
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()

        # Get timeout for this task
        timeout = self.timeouts.get(task.difficulty, 90)

        try:
            # Run the task
            if system == "aorchestra":
                answer, metrics = await asyncio.wait_for(
                    self._run_aorchestra(task, timeout),
                    timeout=timeout,
                )
            elif system == "single_agent":
                answer, metrics = await asyncio.wait_for(
                    self._run_single_agent(task, timeout),
                    timeout=timeout,
                )
            else:  # static_roles
                answer, metrics = await asyncio.wait_for(
                    self._run_static_roles(task, timeout),
                    timeout=timeout,
                )

            # Score the answer
            if task.scoring_method == "exact_match":
                score = score_exact_match(
                    answer,
                    task.expected_answer,
                    case_sensitive=False,
                    ignore_whitespace=True,
                    substring=True,  # Allow substring matching
                )
            else:  # llm_judge
                score = await score_llm_judge(
                    goal=task.goal,
                    answer=answer,
                    client=self.client,
                    model=self.model.name,
                )

            # Calculate latency
            latency = time.time() - start_time

            # Create result
            result = EvaluationResult(
                task_id=task.id,
                task_name=task.name,
                task_category=task.category,
                task_difficulty=task.difficulty,
                system=system,
                answer=answer,
                score=score,
                cost_usd=metrics["cost_usd"],
                latency_seconds=latency,
                total_tokens=metrics["total_tokens"],
                delegation_count=metrics["delegation_count"],
                model_breakdown=metrics["model_breakdown"],
                error=None,
                timestamp=timestamp,
            )

        except asyncio.TimeoutError:
            # Handle timeout
            latency = time.time() - start_time
            result = EvaluationResult(
                task_id=task.id,
                task_name=task.name,
                task_category=task.category,
                task_difficulty=task.difficulty,
                system=system,
                answer="",
                score=0.0,
                cost_usd=0.0,
                latency_seconds=latency,
                total_tokens=0,
                delegation_count=0,
                model_breakdown={},
                error=f"Timeout after {timeout}s",
                timestamp=timestamp,
            )

        except Exception as e:
            # Handle other errors
            latency = time.time() - start_time
            result = EvaluationResult(
                task_id=task.id,
                task_name=task.name,
                task_category=task.category,
                task_difficulty=task.difficulty,
                system=system,
                answer="",
                score=0.0,
                cost_usd=0.0,
                latency_seconds=latency,
                total_tokens=0,
                delegation_count=0,
                model_breakdown={},
                error=str(e),
                timestamp=timestamp,
            )

        return result

    async def run_all(
        self,
        systems: list[Literal["aorchestra", "single_agent", "static_roles"]] = None,
    ) -> dict[str, list[EvaluationResult]]:
        """Run all benchmark tasks for all systems.

        Args:
            systems: List of systems to run (default: all three)

        Returns:
            Dictionary mapping system name to list of EvaluationResult
        """
        if systems is None:
            systems = ["aorchestra", "single_agent", "static_roles"]

        # Clear previous results
        self.results = {system: [] for system in systems}

        # Run all tasks for all systems
        for system in systems:
            for task in self.tasks:
                result = await self._run_benchmark(task, system)
                self.results[system].append(result)

        return self.results

    def get_summary(self) -> dict:
        """Calculate summary statistics for all systems.

        Returns:
            Dictionary with per-system statistics
        """
        summary = {}

        for system, results in self.results.items():
            if not results:
                continue

            # Filter out failed results
            valid_results = [r for r in results if r.error is None]

            if not valid_results:
                summary[system] = {
                    "num_tasks": len(results),
                    "num_failures": len(results),
                    "accuracy": 0.0,
                    "avg_cost_usd": 0.0,
                    "avg_latency_seconds": 0.0,
                    "avg_tokens": 0,
                    "total_delegations": 0,
                }
                continue

            summary[system] = {
                "num_tasks": len(results),
                "num_failures": len(results) - len(valid_results),
                "accuracy": sum(r.score for r in valid_results) / len(valid_results),
                "avg_cost_usd": sum(r.cost_usd for r in valid_results) / len(valid_results),
                "avg_latency_seconds": sum(r.latency_seconds for r in valid_results) / len(valid_results),
                "avg_tokens": sum(r.total_tokens for r in valid_results) // len(valid_results),
                "total_delegations": sum(r.delegation_count for r in valid_results),
            }

        return summary
