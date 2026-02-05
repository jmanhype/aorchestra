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
