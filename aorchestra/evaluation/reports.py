"""Report generation for evaluation results.

Item 005: JSON and markdown report generation.
"""

import json
from datetime import datetime
from typing import Any


def generate_json_report(results: dict, metadata: dict | None = None) -> str:
    """Generate JSON report from evaluation results.

    Args:
        results: Dictionary with evaluation results per strategy.
        metadata: Optional metadata (run date, config, etc.).

    Returns:
        JSON string with formatted report.
    """
    report = {
        "report_type": "aorchestra_evaluation",
        "generated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
        "results": {},
        "summary": {},
    }

    strategy_summaries = []
    for strategy_name, strategy_results in results.items():
        tasks = strategy_results if isinstance(strategy_results, list) else [strategy_results]

        total_score = 0.0
        total_cost = 0.0
        total_tokens = 0
        task_details = []

        for task_result in tasks:
            if isinstance(task_result, dict):
                score = task_result.get("score", 0.0)
                cost = task_result.get("cost_usd", 0.0)
                tokens = task_result.get("total_tokens", 0)
                total_score += score
                total_cost += cost
                total_tokens += tokens
                task_details.append(task_result)

        avg_score = total_score / len(tasks) if tasks else 0.0

        strategy_summary = {
            "strategy": strategy_name,
            "avg_score": round(avg_score, 4),
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "num_tasks": len(tasks),
            "task_details": task_details,
        }
        report["results"][strategy_name] = strategy_summary
        strategy_summaries.append(strategy_summary)

    # Overall summary
    if strategy_summaries:
        best = max(strategy_summaries, key=lambda s: s["avg_score"])
        cheapest = min(strategy_summaries, key=lambda s: s["total_cost_usd"])
        report["summary"] = {
            "best_score_strategy": best["strategy"],
            "best_avg_score": best["avg_score"],
            "cheapest_strategy": cheapest["strategy"],
            "cheapest_cost_usd": cheapest["total_cost_usd"],
            "strategies_compared": len(strategy_summaries),
        }

    return json.dumps(report, indent=2, default=str)


def generate_markdown_report(results: dict, metadata: dict | None = None) -> str:
    """Generate markdown report from evaluation results.

    Args:
        results: Dictionary with evaluation results per strategy.
        metadata: Optional metadata.

    Returns:
        Markdown formatted report string.
    """
    lines = ["# AOrchestra Evaluation Report", ""]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if metadata:
        lines.append("## Configuration")
        for key, value in metadata.items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")

    lines.append("## Results Summary")
    lines.append("")
    lines.append("| Strategy | Avg Score | Total Cost | Total Tokens | Tasks |")
    lines.append("|----------|-----------|------------|--------------|-------|")

    strategy_summaries = []
    for strategy_name, strategy_results in results.items():
        tasks = strategy_results if isinstance(strategy_results, list) else [strategy_results]

        total_score = 0.0
        total_cost = 0.0
        total_tokens = 0

        for task_result in tasks:
            if isinstance(task_result, dict):
                total_score += task_result.get("score", 0.0)
                total_cost += task_result.get("cost_usd", 0.0)
                total_tokens += task_result.get("total_tokens", 0)

        avg_score = total_score / len(tasks) if tasks else 0.0
        lines.append(
            f"| {strategy_name} | {avg_score:.4f} | ${total_cost:.6f} | {total_tokens} | {len(tasks)} |"
        )
        strategy_summaries.append({
            "name": strategy_name,
            "avg_score": avg_score,
            "total_cost": total_cost,
        })

    lines.append("")

    # Winner
    if strategy_summaries:
        best = max(strategy_summaries, key=lambda s: s["avg_score"])
        cheapest = min(strategy_summaries, key=lambda s: s["total_cost"])
        lines.append("## Analysis")
        lines.append("")
        lines.append(f"- **Best accuracy:** {best['name']} (avg score: {best['avg_score']:.4f})")
        lines.append(f"- **Most cost-effective:** {cheapest['name']} (total: ${cheapest['total_cost']:.6f})")
        lines.append("")

    # Per-strategy details
    lines.append("## Detailed Results")
    lines.append("")
    for strategy_name, strategy_results in results.items():
        lines.append(f"### {strategy_name}")
        lines.append("")
        tasks = strategy_results if isinstance(strategy_results, list) else [strategy_results]
        for i, task_result in enumerate(tasks):
            if isinstance(task_result, dict):
                task_name = task_result.get("task", f"Task {i+1}")
                score = task_result.get("score", 0.0)
                lines.append(f"- **{task_name}:** score={score:.4f}")
        lines.append("")

    return "\n".join(lines)
