#!/usr/bin/env python
"""Orchestration demo - shows the full Delegate -> Observe -> Act pattern.

This version uses mock LLM responses to demonstrate the orchestration flow
without depending on external API latency. See real_orchestration_simple.py
for the actual LLM-backed version.
"""
import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class Observation:
    """Result from a sub-agent execution."""
    result_summary: str
    artifacts: dict[str, Any]
    error_logs: list[str]


@dataclass 
class AgentTuple:
    """The 4-tuple defining a sub-agent."""
    instruction: str
    context: str
    tools: list[str]
    model: str


class Orchestrator:
    """Orchestrator that implements the Delegate -> Observe -> Act loop."""
    
    def __init__(self):
        self.step = 0
        self.context = {}
    
    async def solve(self, goal: str) -> str:
        """Solve a complex goal through task decomposition and delegation."""
        
        print(f"\n{'='*60}")
        print("ORCHESTRATOR RECEIVED GOAL:")
        print(f"  {goal}")
        print(f"{'='*60}\n")
        
        # STEP 1: Decompose goal into sub-tasks
        sub_tasks = await self.decompose(goal)
        print(f"DECOMPOSED INTO {len(sub_tasks)} SUB-TASKS:")
        for i, task in enumerate(sub_tasks, 1):
            print(f"  {i}. {task}")
        print()
        
        # STEP 2: Execute via Delegate -> Observe loop
        for task in sub_tasks:
            self.step += 1
            print(f"[STEP {self.step}] {task}")
            
            # DELEGATE: Create sub-agent tuple and execute
            observation = await self.delegate(task)
            
            # OBSERVE: Process observation
            print(f"  Observation: {observation.result_summary}")
            if observation.artifacts:
                print(f"  Artifacts: {observation.artifacts}")
            
            # UPDATE CONTEXT: For next iteration
            self.context[f"step{self.step}"] = observation.artifacts or observation.result_summary
            
            # CHECK: Should we continue or terminate?
            if observation.error_logs:
                print(f"  ERRORS: {observation.error_logs}")
                break
            
            print()
        
        # STEP 3: Synthesize final answer
        final = await self.synthesize(goal)
        
        print(f"{'='*60}")
        print(f"FINAL ANSWER: {final}")
        print(f"{'='*60}")
        
        return final
    
    async def decompose(self, goal: str) -> list[str]:
        """Decompose goal into sub-tasks (would use LLM in production)."""
        # In production: call LLM to decompose
        # Here: simulate decomposition for demo
        await asyncio.sleep(0.1)  # Simulate LLM latency
        
        # Example decomposition for a shopping calculation
        if "shopping" in goal.lower():
            return [
                "Calculate cost of first set of items (3 x $15.99)",
                "Calculate cost of second set of items (2 x $24.50)",
                "Sum the subtotals",
                "Apply 10% discount to total",
                "Add 8% sales tax to discounted amount",
            ]
        elif "multiply" in goal.lower() or "add" in goal.lower():
            return [
                "Calculate 25 * 4",
                "Calculate 18 * 3",
                "Sum the results (100 + 54)",
                "Apply 15% discount (154 * 0.85)",
            ]
        else:
            return [goal]  # Can't decompose, return as-is
    
    async def delegate(self, task: str) -> Observation:
        """Delegate task to a sub-agent (would spawn SubAgent in production)."""
        
        # BUILD TUPLE
        tuple_def = AgentTuple(
            instruction=task,
            context=str(self.context),
            tools=["calculator"],
            model="glm-4.7",
        )
        
        print(f"  Delegate()")
        print(f"    Tuple: instruction='{task[:40]}...'")
        print(f"    Tools: {tuple_def.tools}")
        
        # In production: agent = SubAgent(tuple_def); obs, cost = await agent.execute()
        # Here: simulate execution
        await asyncio.sleep(0.1)
        
        # Simulate tool execution based on task
        result = self._simulate_calculation(task)
        
        return Observation(
            result_summary=f"Calculated: {result}",
            artifacts={"result": result},
            error_logs=[],
        )
    
    def _simulate_calculation(self, task: str) -> float:
        """Simulate calculator tool execution."""
        import re
        
        # Extract numbers from task
        nums = [float(n) for n in re.findall(r'[\d.]+', task)]
        
        if "multiply" in task.lower() or "*" in task or "x" in task.lower():
            if len(nums) >= 2:
                return nums[0] * nums[1]
        elif "sum" in task.lower() or "add" in task.lower() or "+" in task:
            return sum(nums) if nums else 0
        elif "discount" in task.lower():
            # Apply discount to previous result
            prev = self.context.get(f"step{self.step-1}", {})
            if isinstance(prev, dict):
                base = prev.get("result", 0)
            else:
                base = 0
            pct = nums[0] if nums else 10
            return round(base * (1 - pct/100), 2)
        elif "tax" in task.lower():
            prev = self.context.get(f"step{self.step-1}", {})
            if isinstance(prev, dict):
                base = prev.get("result", 0)
            else:
                base = 0
            pct = nums[0] if nums else 8
            return round(base * (1 + pct/100), 2)
        
        # Default: return first number or 0
        return nums[0] if nums else 0
    
    async def synthesize(self, goal: str) -> str:
        """Synthesize final answer from all observations."""
        # Get last result
        last_key = f"step{self.step}"
        if last_key in self.context:
            result = self.context[last_key]
            if isinstance(result, dict):
                return f"${result.get('result', 0):.2f}"
            return str(result)
        return "Could not determine final answer"


async def main():
    orchestrator = Orchestrator()
    
    goal = """Calculate total shopping cost:
    - 3 items at $15.99 each
    - 2 items at $24.50 each
    - Apply 10% discount
    - Add 8% sales tax"""
    
    await orchestrator.solve(goal)


if __name__ == "__main__":
    print("AOrchestra - Delegate -> Observe -> Act Demo")
    print("-" * 60)
    asyncio.run(main())
