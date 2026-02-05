#!/usr/bin/env python
"""Real orchestration example - simpler version with pre-decomposed tasks.

Demonstrates the Delegate() → Observation → Next Action loop with real LLM calls.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.agents import SubAgent
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.tools.builtins import CalculatorTool


async def delegate(task: str, context: str, model: ModelConfig) -> Observation:
    """Delegate() action - spawns a sub-agent and returns Observation."""
    print(f"  -> Delegate({task[:50]}...)")
    
    prompt = f"{task}"
    if context:
        prompt += f"\n\nContext from previous steps: {context}"
    prompt += "\n\nUse the calculator tool. Give just the numeric result."
    
    tuple_def = AgentTuple(
        instruction=prompt,
        context="",
        tools=[CalculatorTool()],
        model=model,
    )
    
    agent = SubAgent(tuple_def)
    obs, cost = await agent.execute()
    
    print(f"  <- Observation: {obs.result_summary[:80]}")
    if obs.artifacts:
        print(f"    Artifacts: {obs.artifacts}")
    
    return obs


async def orchestrate(goal: str, sub_tasks: list[str], model: ModelConfig) -> str:
    """Main orchestration loop: Delegate → Observe → Decide → Repeat."""
    
    print(f"\n{'='*60}")
    print(f"GOAL: {goal}")
    print(f"{'='*60}")
    print(f"\nDecomposed into {len(sub_tasks)} sub-tasks:\n")
    
    context = {}
    
    for i, task in enumerate(sub_tasks, 1):
        print(f"\n[STEP {i}/{len(sub_tasks)}]")
        print(f"  Task: {task}")
        
        # Build context from previous observations
        ctx_str = ", ".join(f"{k}={v}" for k, v in context.items()) if context else ""
        
        # DELEGATE: Spawn sub-agent
        obs = await delegate(task, ctx_str, model)
        
        # OBSERVE: Extract result for next iteration
        # Look for numbers in artifacts or result
        result = None
        for key, val in obs.artifacts.items():
            if isinstance(val, (int, float)):
                result = val
                break
        
        if result is None:
            # Try to parse from result_summary
            import re
            nums = re.findall(r'[\d,]+\.?\d*', obs.result_summary.replace(',', ''))
            if nums:
                result = float(nums[-1])
        
        if result is not None:
            context[f"step{i}"] = result
            print(f"  [OK] Result: {result}")
        else:
            context[f"step{i}"] = obs.result_summary[:50]
            print(f"  [OK] Result: {obs.result_summary[:50]}")
    
    # Final answer is the last result
    final = list(context.values())[-1] if context else "No result"
    
    print(f"\n{'='*60}")
    print(f"FINAL ANSWER: {final}")
    print(f"{'='*60}\n")
    
    return str(final)


async def main():
    api_key = os.environ.get("AORCHESTRA_API_KEY", "")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    if not api_key:
        print("Usage: python real_orchestration_simple.py <api_key>")
        sys.exit(1)
    
    model = ModelConfig(
        name="glm-4.7",
        api_base="https://api.z.ai/api/paas/v4/",
        api_key=api_key,
        max_tokens=512,
    )
    
    # Pre-decomposed goal (normally the orchestrator would do this via LLM)
    goal = "Calculate: (25 × 4) + (18 × 3) - 15% discount"
    
    sub_tasks = [
        "Calculate 25 multiplied by 4",
        "Calculate 18 multiplied by 3", 
        "Add the results from step 1 and step 2",
        "Calculate 15% of the total and subtract it",
    ]
    
    await orchestrate(goal, sub_tasks, model)


if __name__ == "__main__":
    asyncio.run(main())
