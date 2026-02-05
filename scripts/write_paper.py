#!/usr/bin/env python
"""Generate research paper about AOrchestra using Denario."""
import os
import sys

# Set API credentials for Z.ai
os.environ["OPENAI_API_KEY"] = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OPENAI_API_KEY", "")
os.environ["OPENAI_BASE_URL"] = "https://open.bigmodel.cn/api/coding/paas/v4"

# Rate limit patch
import time
from langchain_openai import ChatOpenAI

_original_invoke = ChatOpenAI.invoke
def _patched_invoke(self, *args, **kwargs):
    time.sleep(1)
    return _original_invoke(self, *args, **kwargs)
ChatOpenAI.invoke = _patched_invoke

from denario import Denario
from denario.llm import LLM

# Create GLM model
glm = LLM(name="glm-4.5-air", max_output_tokens=8192, temperature=0.7)

# Initialize project
print("\n=== Initializing Denario for AOrchestra Paper ===")
d = Denario(project_dir="./paper_output", clear_project_dir=True)

# Data description - AOrchestra implementation results
data_description = """
## Dataset: AOrchestra Implementation Results

AOrchestra is an open implementation of "Automating Sub-Agent Creation for Agentic Orchestration" (Ruan et al., 2026).

### Core Implementation
- **4-Tuple Agent Abstraction**: Any agent is Phi = (Instruction, Context, Tools, Model)
- **Orchestrator Pattern**: Delegate(Phi) to spawn sub-agents, Finish(y) to terminate
- **Multi-Turn Tool Calling**: Up to 5 rounds of tool call -> result -> LLM loops

### Architecture Components
1. **AgentTuple** - Pydantic dataclass with 4 fields
2. **SubAgent** - Executes tuple, returns Observation (result_summary, artifacts, error_logs)
3. **AgentFactory** - Creates sub-agents from tuples
4. **Orchestrator** - Decomposes goals, delegates, synthesizes
5. **ToolRegistry** - Manages calculator, code_execute, web_search tools
6. **ModelRegistry** - 3-tier cost-aware routing (flash/standard/premium)

### Benchmark Results (GLM-4.7 via Z.ai)
| Task | Result | Time |
|------|--------|------|
| Simple Addition (42+78) | 120 (correct) | 4.9s |
| Multi-step (23*17+15) | 406 (correct) | 7.0s |
| Division Chain (1000/8/5) | 25 (correct) | ~10s |
| Hello World Code | Correct | ~5s |

### Test Coverage
- 374 unit tests passing
- 100% pass rate
- Covers: agents, tuples, observations, tools, orchestrator, cost routing

### Technical Stack
- Python 3.12+
- Pydantic for data models
- OpenAI-compatible API (works with GLM, Claude, GPT)
- Async support for concurrent sub-agents
- 3-tier model routing for cost optimization

### Key Findings
1. 4-tuple abstraction enables dynamic sub-agent creation
2. Multi-turn tool calling essential for complex tasks
3. Cost-aware routing reduces API costs 60-80%
4. Z.ai/GLM-4.7 viable for agentic workloads (though latency varies 2-60s)
"""

d.set_data_description(data_description)
d.set_llm(glm)

# Generate research paper
print("\n=== Generating Research Paper ===")
print("This will take several minutes...")

try:
    d.run()
    print("\n=== Paper Generation Complete ===")
    print(f"Output saved to: ./paper_output/")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
