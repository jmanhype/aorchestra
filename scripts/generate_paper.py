#!/usr/bin/env python
"""Generate research paper about AOrchestra directly via GLM."""
import asyncio
import sys
import os
from openai import AsyncOpenAI

API_KEY = sys.argv[1] if len(sys.argv) > 1 else ""
API_BASE = "https://api.z.ai/api/paas/v4/"

PAPER_SECTIONS = [
    ("abstract", """Write a research paper abstract (150-200 words) for:

Title: AOrchestra: Automating Sub-Agent Creation for Agentic Orchestration

Key contributions:
1. 4-tuple agent abstraction: Phi = (Instruction, Context, Tools, Model)
2. Orchestrator pattern with Delegate(Phi) and Finish(y) actions
3. Multi-turn tool calling (up to 5 rounds)
4. Cost-aware 3-tier model routing (flash/standard/premium)
5. 374 passing tests, real benchmarks with GLM-4.7

Write a formal academic abstract."""),

    ("introduction", """Write the Introduction section (300-400 words) for a paper on AOrchestra.

Context:
- Large Language Models enable agentic systems
- Challenge: How to decompose complex tasks and coordinate multiple agents
- Solution: Dynamic sub-agent creation via 4-tuple abstraction

Cover:
1. Motivation and problem statement
2. Key insight (any agent = 4-tuple)
3. Contributions overview
4. Paper organization"""),

    ("methodology", """Write the Methodology section (400-500 words) covering:

1. Agent Tuple Abstraction
   - Phi = (Instruction, Context, Tools, Model)
   - AgentTuple dataclass with Pydantic
   - SubAgent.execute() returns Observation

2. Orchestrator Architecture
   - Goal decomposition
   - Delegate(Phi) spawns sub-agents
   - Finish(y) terminates with answer
   - Observation -> next action loop

3. Multi-Turn Tool Calling
   - Up to 5 rounds of tool call -> result -> LLM
   - Message history accumulation
   - Artifact tracking per round

4. Cost-Aware Model Routing
   - 3-tier: Flash, Standard, Premium
   - Complexity-based selection
   - Lambda parameter for cost sensitivity"""),

    ("experiments", """Write the Experiments section (300-400 words) with:

Setup:
- GLM-4.7 via Z.ai API
- 12 benchmark tasks (math, code, research)
- Calculator, CodeExecute, WebSearch tools

Results Table:
| Task | Expected | Result | Time |
|------|----------|--------|------|
| Simple Addition (42+78) | 120 | 120 ✓ | 4.9s |
| Multi-step (23*17+15) | 406 | 406 ✓ | 7.0s |
| Division Chain (1000/8/5) | 25 | 25 ✓ | ~10s |
| Hello World Code | print output | ✓ | ~5s |

Test Coverage:
- 374 unit tests passing
- Covers all components

Analysis:
- Multi-turn essential for complex tasks
- Z.ai latency varies 2-60s
- Cost savings 60-80% with 3-tier routing"""),

    ("conclusion", """Write a Conclusion section (150-200 words) summarizing:

1. Key contributions
   - 4-tuple agent abstraction
   - Dynamic sub-agent orchestration
   - Cost-aware model selection

2. Findings
   - Pattern works for multi-step tasks
   - Tool calling critical for grounding
   - Cost optimization achievable

3. Future work
   - Parallel sub-agent execution
   - Learned orchestration policies
   - Broader tool ecosystem"""),
]


async def generate_section(client, name, prompt):
    print(f"\nGenerating {name}...", flush=True)
    response = await client.chat.completions.create(
        model="glm-4.7",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        temperature=0.7,
    )
    return response.choices[0].message.content


async def main():
    if not API_KEY:
        print("Usage: python generate_paper.py <api_key>")
        sys.exit(1)
    
    client = AsyncOpenAI(api_key=API_KEY, base_url=API_BASE)
    
    paper = []
    paper.append("# AOrchestra: Automating Sub-Agent Creation for Agentic Orchestration\n")
    paper.append("*Open implementation and empirical evaluation*\n")
    paper.append("---\n")
    
    for name, prompt in PAPER_SECTIONS:
        try:
            content = await asyncio.wait_for(
                generate_section(client, name, prompt),
                timeout=120
            )
            paper.append(f"\n## {name.title()}\n")
            paper.append(content)
            paper.append("\n")
            print(f"  Done: {len(content)} chars", flush=True)
        except asyncio.TimeoutError:
            paper.append(f"\n## {name.title()}\n")
            paper.append("[Section generation timed out]\n")
            print(f"  Timeout on {name}", flush=True)
        except Exception as e:
            print(f"  Error on {name}: {e}", flush=True)
    
    # Save paper
    output_path = "paper_output/aorchestra_paper.md"
    os.makedirs("paper_output", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(paper))
    
    print(f"\n=== Paper saved to {output_path} ===")


if __name__ == "__main__":
    asyncio.run(main())
