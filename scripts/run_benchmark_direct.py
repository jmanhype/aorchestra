"""Direct benchmark runner - bypasses eval framework for speed."""
import asyncio
import sys
import time
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.agents import SubAgent
from aorchestra.models.config import ModelConfig
from aorchestra.tools.builtins import CalculatorTool, CodeExecuteTool, WebSearchMockTool

API_KEY = sys.argv[1] if len(sys.argv) > 1 else ""
API_BASE = "https://api.z.ai/api/paas/v4/"

TASKS = [
    ("Simple Addition", "What is 42 + 78? Use the calculator tool.", "120", ["calculator"]),
    ("Multiplication+Addition", "Calculate 23 * 17 + 15. Use the calculator for each step.", "406", ["calculator"]),
    ("Division Chain", "Calculate 1000 / 8 / 5 using the calculator. Do one division at a time.", "25", ["calculator"]),
    ("Complex Arithmetic", "Calculate (45 * 12) + (87 - 26) + 121. Use calculator for each step.", "662", ["calculator"]),
    ("Hello World", "Write a Python program that prints 'Hello, World!'", "Hello, World!", ["code_execute"]),
    ("Sum 1-100", "Write Python code to calculate the sum of numbers 1 to 100. Print just the number.", "5050", ["code_execute"]),
    ("Fibonacci", "Write Python to generate first 10 Fibonacci numbers starting from 0. Print them comma-separated.", "0, 1, 1, 2, 3, 5, 8, 13, 21, 34", ["code_execute"]),
    ("Quadratic", "Solve x^2 - 5x + 6 = 0. What are the roots? The smaller root is:", "2", ["code_execute"]),
    ("Python Info", "What language was created by Guido van Rossum? Just name the language.", "Python", []),
    ("Asyncio Info", "In Python asyncio, what keyword defines a coroutine function? Just the keyword.", "async", []),
    ("Division Simple", "What is 144 / 12? Use the calculator.", "12", ["calculator"]),
    ("Rectangle Area", "Calculate the area of a rectangle with sides 15 and 23. Use calculator.", "345", ["calculator"]),
]

TOOL_MAP = {
    "calculator": CalculatorTool,
    "code_execute": CodeExecuteTool,
    "web_search_mock": WebSearchMockTool,
}


async def run_task(name, goal, expected, tool_names, model_config):
    tools = [TOOL_MAP[t]() for t in tool_names if t in TOOL_MAP]
    t = AgentTuple(instruction=goal, context="", tools=tools, model=model_config)
    agent = SubAgent(t)
    
    start = time.time()
    try:
        obs, cost = await asyncio.wait_for(agent.execute(), timeout=90)
        elapsed = time.time() - start
        answer = obs.result_summary or ""
        
        # Check if expected is in answer (case insensitive)
        passed = expected.lower() in answer.lower()
        
        return {
            "name": name,
            "passed": passed,
            "answer": answer[:120],
            "expected": expected,
            "elapsed": elapsed,
            "tokens": cost.total_tokens,
        }
    except asyncio.TimeoutError:
        return {"name": name, "passed": False, "answer": "TIMEOUT", "expected": expected, "elapsed": 90, "tokens": 0}
    except Exception as e:
        return {"name": name, "passed": False, "answer": f"ERROR: {e}", "expected": expected, "elapsed": time.time()-start, "tokens": 0}


async def main():
    m = ModelConfig(name="glm-4.7", api_base=API_BASE, api_key=API_KEY, max_tokens=2048)
    
    results = []
    passed = 0
    total = len(TASKS)
    
    for name, goal, expected, tools in TASKS:
        print(f"  [{len(results)+1}/{total}] {name}...", end=" ", flush=True)
        r = await run_task(name, goal, expected, tools, m)
        results.append(r)
        
        mark = "PASS" if r["passed"] else "FAIL"
        if r["passed"]:
            passed += 1
        print(f"{mark} ({r['elapsed']:.1f}s, {r['tokens']} tok)", flush=True)
        if not r["passed"]:
            print(f"        got: {r['answer'][:80]}", flush=True)
            print(f"        exp: {r['expected']}", flush=True)
    
    print(f"\n{'='*50}")
    print(f"SCORE: {passed}/{total} = {passed/total*100:.0f}%")
    print(f"{'='*50}")
    
    # Save results
    with open("results/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())
