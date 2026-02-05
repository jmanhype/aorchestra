#!/usr/bin/env python
"""Real orchestration example - actually runs multi-step delegation.

This demonstrates:
1. Orchestrator receiving a complex goal
2. Decomposing into sub-tasks via Delegate()
3. Sub-agents executing and returning Observations
4. Orchestrator using observations to decide next action
5. Full observation → action loop until goal complete
"""
import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.agents import SubAgent
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.tools.builtins import CalculatorTool


class Orchestrator:
    """Real orchestrator that decomposes goals and delegates to sub-agents."""
    
    def __init__(self, model_config: ModelConfig):
        self.model = model_config
        self.history: list[dict] = []
        self.max_steps = 10
    
    async def solve(self, goal: str) -> str:
        """Solve a complex goal through delegation and observation loop."""
        print(f"\n{'='*60}")
        print(f"ORCHESTRATOR: Received goal")
        print(f"  \"{goal}\"")
        print(f"{'='*60}\n")
        
        # Step 1: Decompose the goal into sub-tasks
        sub_tasks = await self._decompose_goal(goal)
        print(f"ORCHESTRATOR: Decomposed into {len(sub_tasks)} sub-tasks:")
        for i, task in enumerate(sub_tasks, 1):
            print(f"  {i}. {task}")
        print()
        
        # Step 2: Execute sub-tasks through delegation loop
        results = {}
        for step, task in enumerate(sub_tasks, 1):
            print(f"STEP {step}: Delegating sub-task")
            print(f"  Task: {task}")
            
            # Create Delegate() - spawn sub-agent
            observation = await self._delegate(task, context=str(results))
            
            print(f"  Observation: {observation.result_summary[:100]}")
            if observation.artifacts:
                print(f"  Artifacts: {observation.artifacts}")
            
            # Store result for next iteration
            results[f"step_{step}"] = {
                "task": task,
                "result": observation.result_summary,
                "artifacts": observation.artifacts,
            }
            
            # Check if we should continue or terminate
            if observation.error_logs:
                print(f"  ⚠️  Errors: {observation.error_logs}")
            print()
        
        # Step 3: Synthesize final answer
        final_answer = await self._synthesize(goal, results)
        
        print(f"{'='*60}")
        print(f"FINAL ANSWER: {final_answer}")
        print(f"{'='*60}")
        
        return final_answer
    
    async def _decompose_goal(self, goal: str) -> list[str]:
        """Use LLM to decompose goal into sub-tasks."""
        decompose_prompt = f"""Break down this goal into simple sequential sub-tasks.
Each sub-task should be a single action that can be done with a calculator.
Return ONLY a numbered list, nothing else.

Goal: {goal}

Sub-tasks:"""
        
        tuple_def = AgentTuple(
            instruction=decompose_prompt,
            context="",
            tools=[],
            model=self.model,
        )
        agent = SubAgent(tuple_def)
        obs, _ = await agent.execute()
        
        # Parse numbered list from response
        lines = obs.result_summary.strip().split('\n')
        tasks = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                task = line.lstrip('0123456789.-) ').strip()
                if task:
                    tasks.append(task)
        
        return tasks if tasks else [goal]  # Fallback to original goal
    
    async def _delegate(self, task: str, context: str = "") -> Observation:
        """Delegate a sub-task to a sub-agent with tools."""
        delegate_prompt = f"""{task}

Use the calculator tool to compute any math. Give just the result."""
        
        if context and context != "{}":
            delegate_prompt += f"\n\nPrevious results for reference:\n{context}"
        
        tuple_def = AgentTuple(
            instruction=delegate_prompt,
            context="",
            tools=[CalculatorTool()],
            model=self.model,
        )
        
        agent = SubAgent(tuple_def)
        observation, cost = await agent.execute()
        
        self.history.append({
            "action": "Delegate",
            "task": task,
            "observation": observation.result_summary,
            "tokens": cost.total_tokens,
        })
        
        return observation
    
    async def _synthesize(self, original_goal: str, results: dict) -> str:
        """Synthesize final answer from all sub-task results."""
        results_text = "\n".join(
            f"- {r['task']}: {r['result'][:100]}" 
            for r in results.values()
        )
        
        synth_prompt = f"""Original goal: {original_goal}

Results from sub-tasks:
{results_text}

Provide the final answer to the original goal. Be concise."""
        
        tuple_def = AgentTuple(
            instruction=synth_prompt,
            context="",
            tools=[],
            model=self.model,
        )
        agent = SubAgent(tuple_def)
        obs, _ = await agent.execute()
        
        return obs.result_summary


async def main():
    # Get API key from env or args
    api_key = os.environ.get("AORCHESTRA_API_KEY", "")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    if not api_key:
        print("Usage: python real_orchestration.py <api_key>")
        print("Or set AORCHESTRA_API_KEY environment variable")
        sys.exit(1)
    
    # Configure model
    model = ModelConfig(
        name="glm-4.7",
        api_base="https://api.z.ai/api/paas/v4/",
        api_key=api_key,
        max_tokens=1024,
    )
    
    # Create orchestrator
    orchestrator = Orchestrator(model)
    
    # Complex multi-step goal
    goal = """Calculate the total cost of a shopping trip:
    - 3 items at $15.99 each
    - 2 items at $24.50 each  
    - Apply a 10% discount to the total
    - Add 8% sales tax to the discounted total
    What is the final amount to pay?"""
    
    # Run orchestration
    answer = await orchestrator.solve(goal)
    
    # Print execution history
    print(f"\n📊 Execution History ({len(orchestrator.history)} delegations):")
    total_tokens = 0
    for i, h in enumerate(orchestrator.history, 1):
        print(f"  {i}. {h['task'][:50]}... ({h['tokens']} tokens)")
        total_tokens += h['tokens']
    print(f"  Total tokens: {total_tokens}")


if __name__ == "__main__":
    asyncio.run(main())
