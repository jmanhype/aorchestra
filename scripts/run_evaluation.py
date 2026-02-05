#!/usr/bin/env python
"""Run AOrchestra evaluation benchmark.

Usage:
    python scripts/run_evaluation.py [--strategies single,static,orchestrator]
                                      [--output-dir results/]
                                      [--model glm-4.7]
                                      [--api-base https://api.z.ai/v1]
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from aorchestra.evaluation.tasks import get_benchmark_tasks
from aorchestra.evaluation.baselines import SingleAgentBaseline, StaticRolesBaseline
from aorchestra.evaluation.scoring import score_exact_match
from aorchestra.evaluation.reports import generate_json_report, generate_markdown_report
from aorchestra.models.config import ModelConfig
from aorchestra.tools import ToolRegistry
from aorchestra.tools.builtins import get_builtin_tools_metadata


def parse_args():
    parser = argparse.ArgumentParser(description="Run AOrchestra evaluation benchmark")
    parser.add_argument(
        "--strategies",
        default="single,static",
        help="Comma-separated strategies to evaluate (single,static,orchestrator)",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory to write reports to",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("AORCHESTRA_MODEL", "glm-4.7"),
        help="Model name to use",
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("AORCHESTRA_API_BASE", "https://api.z.ai/api/paas/v4/"),
        help="API base URL",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("AORCHESTRA_API_KEY", ""),
        help="API key",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tasks without executing",
    )
    return parser.parse_args()


async def run_strategy(strategy_name: str, model_config: ModelConfig, tasks: list) -> list:
    """Run a single strategy against all tasks."""
    results = []

    # Create tool registry with builtins
    registry = ToolRegistry()
    for metadata, tool_cls in get_builtin_tools_metadata():
        registry.register(tool_cls(), metadata)

    if strategy_name == "single":
        baseline = SingleAgentBaseline(model=model_config, tool_registry=registry)
    elif strategy_name == "static":
        baseline = StaticRolesBaseline(model=model_config, tool_registry=registry)
    else:
        print(f"  Unknown strategy: {strategy_name}, skipping")
        return results

    for task in tasks:
        print(f"  Running task: {task.name}...")
        try:
            answer, cost_record = await baseline.solve(
                goal=task.goal,
                tool_names=task.tools or [],
                context="",
            )
            # Use substring matching — LLM answers are verbose
            score = score_exact_match(answer or "", task.expected_answer, substring=True)

            result = {
                "task": task.name,
                "category": task.category,
                "answer": answer or "",
                "expected": task.expected_answer,
                "score": score,
                "cost_usd": cost_record.estimated_cost_usd if cost_record else 0.0,
                "total_tokens": cost_record.total_tokens if cost_record else 0,
            }
            results.append(result)
            print(f"    Score: {score:.2f} | Cost: ${result['cost_usd']:.6f}")
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({
                "task": task.name,
                "category": task.category,
                "answer": "",
                "expected": task.expected_answer,
                "score": 0.0,
                "cost_usd": 0.0,
                "total_tokens": 0,
                "error": str(e),
            })

    return results


async def main():
    args = parse_args()
    tasks = get_benchmark_tasks()
    strategies = [s.strip() for s in args.strategies.split(",")]

    print(f"AOrchestra Evaluation Benchmark")
    print(f"Model: {args.model}")
    print(f"API Base: {args.api_base}")
    print(f"Strategies: {strategies}")
    print(f"Tasks: {len(tasks)}")
    print()

    if args.dry_run:
        print("DRY RUN — Tasks:")
        for task in tasks:
            print(f"  - [{task.category}] {task.name}: {task.goal[:60]}...")
        return

    model_config = ModelConfig(
        name=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        max_tokens=2048,  # GLM uses reasoning tokens, needs headroom
    )

    all_results = {}
    for strategy_name in strategies:
        print(f"\n=== Strategy: {strategy_name} ===")
        results = await run_strategy(strategy_name, model_config, tasks)
        all_results[strategy_name] = results

    # Generate reports
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "model": args.model,
        "api_base": args.api_base,
        "strategies": strategies,
        "num_tasks": len(tasks),
        "run_date": datetime.now().isoformat(),
    }

    # JSON report
    json_report = generate_json_report(all_results, metadata)
    json_path = output_dir / "evaluation_report.json"
    json_path.write_text(json_report)
    print(f"\nJSON report: {json_path}")

    # Markdown report
    md_report = generate_markdown_report(all_results, metadata)
    md_path = output_dir / "evaluation_report.md"
    md_path.write_text(md_report)
    print(f"Markdown report: {md_path}")

    # Print summary
    print("\n=== Summary ===")
    for strategy, results in all_results.items():
        if results:
            avg_score = sum(r["score"] for r in results) / len(results)
            total_cost = sum(r["cost_usd"] for r in results)
            print(f"  {strategy}: avg_score={avg_score:.4f}, cost=${total_cost:.6f}")


if __name__ == "__main__":
    asyncio.run(main())
