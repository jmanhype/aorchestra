# Research: Evaluation harness and demo

**Date**: 2025-02-04
**Item**: 005-evaluation-harness-demo

## Research Question

Create a benchmark evaluation suite with 10+ diverse tasks. Implement automated scoring. Run against baselines. Generate comparison report.

## Summary

Item 005 implements a **comprehensive evaluation harness** to demonstrate and measure AOrchestra's effectiveness compared to baseline approaches. The foundation (items 001-004) is complete and production-ready, with all core components including the Orchestrator, ToolRegistry, ModelRegistry, and cost tracking infrastructure.

The evaluation harness must:
1. **Define 10+ diverse benchmark tasks** spanning math, code, research, and planning domains
2. **Implement baseline agents** for comparison:
   - Single-agent baseline (no delegation, direct LLM calls)
   - Static-roles baseline (fixed sub-agents with predefined tools)
3. **Automate scoring** using two approaches:
   - Exact match scoring for tasks with deterministic answers
   - LLM-as-judge scoring for open-ended tasks (evaluates answer quality)
4. **Run comprehensive benchmarks** across both AOrchestra and baselines
5. **Generate machine-readable reports** (JSON for Denario pipeline, markdown for human review)
6. **Track metrics**: accuracy, cost (USD), latency (seconds), token usage

The evaluation harness leverages existing infrastructure:
- Orchestrator with cost tracking (`orchestrator.py:50-53`, `orchestrator.py:95-100`)
- OrchestratorState.get_cost_summary() for per-run metrics (`state.py:80-106`)
- CostTracker for aggregate cost tracking (`cost.py:100-174`)
- ModelRegistry with built-in models for configurable tiers (`registry.py:90-167`)
- ToolRegistry with 4 built-in tools for task variety (`builtins.py:1-225`)

## Current State Analysis

### Existing Implementation

**Items 001-004 are complete and production-ready** - all infrastructure for evaluation exists:

**Core Infrastructure:**

- **aorchestra/core/orchestrator.py:1-376** - Orchestrator with cost tracking
  - Lines 36-40: Constructor accepts lambda_param for cost-performance tuning
  - Lines 46-59: `_create_default_model_registry()` initializes ModelRegistry
  - Lines 64-67: `_create_default_tool_registry()` initializes ToolRegistry
  - Lines 78-103: `run()` method executes orchestrator and logs total cost/tokens (lines 86-92, 96-101)
  - Lines 105-168: `_decide_action()` uses LLM with function calling for Delegate/Finish decisions
  - Lines 170-251: `_delegate()` executes sub-agent, tracks cost, returns Observation + CostRecord
  - Lines 253-281: `_integrate_observation()` updates state with cost information

- **aorchestra/orchestrator/state.py:1-106** - OrchestratorState with cost summaries
  - Lines 16-60: `Delegation` model with tuple, observation, cost_record, timestamp
  - Lines 63-106: `OrchestratorState` with goal, step, history, max_steps, total_cost_usd
  - Lines 85-106: `get_cost_summary()` returns comprehensive metrics (total_cost_usd, total_tokens, delegation_count, model_breakdown)

- **aorchestra/models/cost.py:1-174** - Cost tracking models
  - Lines 12-54: `CostRecord` with model_name, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, timestamp
  - Lines 57-92: `ModelTier` with tier, cost rates, capabilities
  - Lines 95-110: `ModelSelectionCriteria` with complexity, lambda_param, tier_preference
  - Lines 113-174: `CostTracker` with track(), get_total_cost(), get_total_tokens(), get_summary(), reset()

**Tools and Models:**

- **aorchestra/tools/builtins.py:1-225** - Four built-in tools for benchmark tasks
  - Lines 10-44: `CalculatorTool` - arithmetic operations (math benchmarks)
  - Lines 47-115: `CodeExecuteTool` - safe Python execution (code benchmarks)
  - Lines 118-198: `WebSearchMockTool` - mock search results (research benchmarks)
  - Lines 201-255: `FileReadTool` - safe file reading (planning/file benchmarks)
  - Lines 258-293: `get_builtin_tools_metadata()` returns all tools with metadata

- **aorchestra/models/registry.py:1-167** - ModelRegistry with 3 tiers
  - Lines 90-167: `get_builtin_models()` returns 3 models (glm-4-flash, glm-4.7, glm-4-plus) with cost rates
  - Lines 32-86: `select_model()` implements lambda-based model selection
  - Lines 13-30: register(), get(), get_by_tier(), get_all() methods

- **aorchestra/tools/registry.py:1-219** - ToolRegistry for task setup
  - Lines 52-174: ToolRegistry with register(), get(), select_tools()
  - Lines 12-47: ToolMetadata and ToolSelectionCriteria models
  - Lines 176-219: get_builtin_tools_metadata() returns 4 built-in tools

**Testing Patterns:**

- **tests/test_orchestrator.py:1-176** - Orchestrator testing patterns
  - Lines 31-45: test_run_returns_finish_action_answer() - mocks _decide_action to test run loop
  - Lines 47-59: test_run_initializes_state() - verifies state initialization
  - Lines 61-82: test_max_steps_raises_error() - tests max_steps constraint
  - Lines 84-126: test_delegate_creates_tuple_and_executes() - tests delegation with CostRecord
  - Lines 128-176: test_integrate_observation_updates_state() - verifies cost tracking

- **tests/test_cost_tracker.py:1-245** - CostTracker testing patterns
  - Lines 11-32: test_init_empty() - empty tracker state
  - Lines 34-67: test_track_multiple_records() - multi-record aggregation
  - Lines 115-183: test_get_summary() - comprehensive breakdown with model_breakdown
  - Shows pattern for aggregating costs across multiple runs

- **tests/conftest.py:1-23** - Test fixtures
  - Lines 13-23: mock_openai_response() fixture for LLM mocking
  - Pattern to follow for mocking LLM in evaluation tests

**Configuration:**

- **aorchestra/config.py:1-53** - Configuration management
  - Lines 11-16: Config dataclass with zai_api_key, zai_api_base, zai_model
  - Lines 19-50: from_env() loads from environment variables, parses COST_RATES JSON, LAMBDA parameter
  - Lines 23-44: Cost rates validation with fallback to defaults

- **.env.example:1-21** - Environment variable template
  - Lines 4-6: ZAI_API_KEY, ZAI_API_BASE, ZAI_MODEL
  - Lines 9-12: LAMBDA parameter (cost-performance trade-off)
  - Lines 15-21: COST_RATES JSON for custom model pricing

**No Evaluation Infrastructure Exists:**

- No benchmark task definitions
- No baseline agent implementations
- No scoring mechanisms (exact match or LLM-as-judge)
- No evaluation harness or benchmark runner
- No report generation (JSON or markdown)
- No comparison logic between AOrchestra and baselines

### Current Patterns and Conventions

**Established patterns from items 001-004:**

1. **Pydantic models for all data structures** - CostRecord, OrchestratorState, Delegation, ToolMetadata, ModelTier all use Pydantic
   - Enables JSON serialization for reports
   - Validation ensures data integrity
   - Should use for benchmark tasks, evaluation results

2. **Async-first design** - All orchestrator operations are async
   - Orchestrator.run() is async (orchestrator.py:78)
   - SubAgent.execute() is async
   - Evaluation harness should use async execution for parallel benchmark runs

3. **Cost tracking integration** - Cost tracked at multiple levels
   - CostRecord per delegation (cost.py:12-54)
   - CostTracker aggregates across runs (cost.py:113-174)
   - OrchestratorState.get_cost_summary() provides per-run breakdown (state.py:85-106)
   - Evaluation should capture all three levels

4. **Mock-based testing** - Tests use mocked OpenAI responses
   - conftest.py mock_openai_response() pattern
   - Evaluation should use real LLMs but allow mocking for reproducibility

5. **Factory pattern** - AgentFactory creates agents (factory.py:18-52)
   - Baseline agents should follow similar pattern
   - Evaluation harness creates both AOrchestra and baseline agents

6. **Registry pattern** - ToolRegistry and ModelRegistry manage resources
   - get_builtin_tools_metadata() (tools/builtins.py:258-293)
   - get_builtin_models() (models/registry.py:90-167)
   - Evaluation should use these registries for setup

7. **Configuration from environment** - Config.from_env() loads settings (config.py:19-50)
   - Evaluation should support environment configuration
   - Lambda parameter, cost rates should be configurable

### Integration Points

**Item 005 must integrate with:**

1. **Orchestrator** (core/orchestrator.py)
   - Use for AOrchestra baseline evaluation
   - Access Orchestrator.state for metrics (orchestrator.py:78-103)
   - Access cost_tracker for aggregate costs (orchestrator.py:66)

2. **OrchestratorState.get_cost_summary()** (orchestrator/state.py:85-106)
   - Extract per-run metrics: total_cost_usd, total_tokens, delegation_count, model_breakdown
   - Core data source for evaluation reports

3. **CostTracker** (models/cost.py:113-174)
   - Track costs across multiple benchmark runs
   - get_summary() returns comprehensive breakdown
   - Reset between benchmarks to isolate results

4. **ModelRegistry** (models/registry.py)
   - Configure models for baselines
   - get_builtin_models() for built-in model configurations
   - Select specific tiers for controlled comparison

5. **ToolRegistry** (tools/registry.py)
   - Register tools for benchmark tasks
   - Select tools for baseline agents
   - get_builtin_tools_metadata() for tool setup

6. **Tool implementations** (tools/builtins.py)
   - CalculatorTool for math benchmarks
   - CodeExecuteTool for code benchmarks
   - WebSearchMockTool for research benchmarks
   - FileReadTool for file/planning benchmarks

**No downstream dependencies** - Item 005 is the final item in the series.

## Key Files

### Core Infrastructure

- **aorchestra/core/orchestrator.py:1-376** - Main orchestrator to evaluate
  - Lines 36-40: Constructor with lambda_param for cost-performance tuning
  - Lines 78-103: run() method - main execution loop with cost logging
  - Lines 170-251: _delegate() - sub-agent execution with cost tracking
  - Returns final answer string and populates state with cost records

- **aorchestra/orchestrator/state.py:85-106** - Cost summary extraction
  - get_cost_summary() returns dict with:
    - total_cost_usd: float
    - total_tokens: int
    - delegation_count: int
    - model_breakdown: dict[str, dict[str, float | int]]

- **aorchestra/models/cost.py:1-174** - Cost tracking models
  - Lines 12-54: CostRecord - per-call cost data
  - Lines 113-174: CostTracker - aggregate cost tracking
  - Lines 158-172: get_summary() returns breakdown with model_breakdown

- **aorchestra/models/registry.py:90-167** - Built-in models
  - get_builtin_models() returns 3 models (flash, standard, premium)
  - Each with cost_per_1k_input, cost_per_1k_output
  - Used for baseline agent configuration

- **aorchestra/tools/builtins.py:1-293** - Built-in tools for benchmarks
  - Lines 10-44: CalculatorTool - math operations
  - Lines 47-115: CodeExecuteTool - Python code execution
  - Lines 118-198: WebSearchMockTool - mock web search
  - Lines 201-255: FileReadTool - file reading
  - Lines 258-293: get_builtin_tools_metadata() - tool metadata

- **aorchestra/core/factory.py:18-52** - AgentFactory for baseline creation
  - create() instantiates SubAgent from AgentTuple
  - create_and_execute() executes and returns (Observation, CostRecord)
  - Useful for single-agent baseline

### Test Patterns

- **tests/test_orchestrator.py:31-82** - Orchestrator execution testing
  - Shows how to mock _decide_action for deterministic testing
  - Pattern for testing run() method with mocked LLM

- **tests/test_cost_tracker.py:115-183** - Cost aggregation testing
  - Shows how to aggregate costs across multiple runs
  - Pattern for model_breakdown verification

- **tests/conftest.py:13-23** - Mock OpenAI responses
  - mock_openai_response() fixture
  - Pattern for deterministic LLM testing

### Configuration

- **aorchestra/config.py:19-50** - Environment configuration
  - from_env() loads ZAI_API_KEY, ZAI_API_BASE, ZAI_MODEL, LAMBDA, COST_RATES
  - Cost rates default to estimates if not provided
  - Evaluation should read these for configurable benchmarks

- **.env.example:9-21** - Cost configuration template
  - LAMBDA parameter (0.0-1.0)
  - COST_RATES JSON with model pricing
  - Should be documented for evaluation users

### Item Definition

- **.wreckit/items/005-evaluation-harness-demo/item.json:1-1** - Item requirements
  - Success criteria: 10+ benchmark tasks, automated scoring, baseline comparison, JSON + markdown reports
  - Metrics: accuracy, cost, latency
  - Technical constraints: Depends on items 001-004, must produce machine-readable results for Denario pipeline

## Technical Considerations

### Dependencies

**External Dependencies (already installed):**

1. **pydantic>=2.0** - For evaluation result models
   - Use for BenchmarkTask, EvaluationResult, ComparisonReport
   - JSON serialization for Denario pipeline

2. **openai>=1.0** - For LLM-as-judge scoring
   - Use for evaluating open-ended task answers
   - Same client as orchestrator, can share configuration

3. **asyncio** - For parallel benchmark execution
   - Run multiple benchmarks concurrently
   - Already used throughout codebase

4. **time / datetime** - For latency tracking
   - Measure start/end times for each benchmark
   - Standard library, already used in cost.py:18

**Internal Dependencies (from items 001-004):**

1. **Orchestrator** (core/orchestrator.py)
   - Main system to evaluate
   - Use run(goal) method for execution
   - Extract state for metrics

2. **OrchestratorState** (orchestrator/state.py)
   - get_cost_summary() for metrics
   - history for task trace analysis

3. **CostTracker** (models/cost.py)
   - Track costs across benchmarks
   - get_summary() for aggregate metrics

4. **ModelRegistry** (models/registry.py)
   - Configure models for baselines
   - get_builtin_models() for built-in configs

5. **ToolRegistry** (tools/registry.py)
   - Register tools for benchmarks
   - get_builtin_tools_metadata() for tool setup

6. **Tool implementations** (tools/builtins.py)
   - CalculatorTool, CodeExecuteTool, WebSearchMockTool, FileReadTool
   - Use for diverse benchmark categories

### Patterns to Follow

**From items 001-004:**

1. **Pydantic models for evaluation data**
   ```python
   class BenchmarkTask(BaseModel):
       id: str
       name: str
       category: str  # "math", "code", "research", "planning"
       goal: str
       expected_answer: Optional[str]  # For exact match scoring
       tools: list[str]  # Tools to make available
       scoring_method: Literal["exact_match", "llm_judge"]
       difficulty: Literal["easy", "medium", "hard"]
   ```

2. **Async execution for benchmarks**
   ```python
   async def run_benchmark(task: BenchmarkTask, system: str) -> EvaluationResult:
       start_time = time.time()
       answer = await orchestrator.run(task.goal)
       end_time = time.time()
       latency = end_time - start_time
       cost_summary = orchestrator.state.get_cost_summary()
       return EvaluationResult(...)
   ```

3. **Cost tracking integration**
   ```python
   # Track cost per benchmark
   cost_record = orchestrator.state.get_cost_summary()

   # Track cost across all benchmarks
   cost_tracker = CostTracker()
   for result in results:
       cost_tracker.track(result.cost_record)
   ```

4. **Mock-based testing**
   ```python
   # Mock LLM for deterministic benchmarks (optional)
   with patch.object(orchestrator, "_decide_action") as mock_decide:
       mock_decide.return_value = FinishAction(...)
       result = await orchestrator.run(goal)
   ```

5. **Configuration from environment**
   ```python
   config = Config.from_env()
   lambda_param = config.lambda_param  # Use for orchestrator configuration
   cost_rates = config.cost_rates  # Use for model registry
   ```

**New patterns for item 005:**

1. **Baseline agent implementations**
   ```python
   # Single-agent baseline (no delegation)
   class SingleAgentBaseline:
       def __init__(self, model: ModelConfig, tools: list):
           self.agent = SubAgent(AgentTuple(...))
       async def solve(self, goal: str) -> str:
           return await self.agent.execute()

   # Static-roles baseline (fixed sub-agents)
   class StaticRolesBaseline:
       def __init__(self, agents: dict[str, SubAgent]):
           self.agents = agents  # {"math": SubAgent(...), "code": SubAgent(...)}
       async def solve(self, goal: str) -> str:
           # Simple LLM call to select agent, then delegate
           pass
   ```

2. **Scoring mechanisms**
   ```python
   # Exact match scoring
   def score_exact_match(actual: str, expected: str) -> float:
       return 1.0 if actual.strip() == expected.strip() else 0.0

   # LLM-as-judge scoring
   async def score_llm_judge(goal: str, answer: str) -> float:
       prompt = f"Rate this answer (0.0-1.0): Goal={goal}, Answer={answer}"
       response = await llm_client.chat.completions.create(...)
       return float(response.choices[0].message.content)
   ```

3. **Report generation**
   ```python
   # JSON report (machine-readable for Denario)
   def generate_json_report(results: list[EvaluationResult]) -> str:
       return json.dumps([r.model_dump() for r in results], indent=2)

   # Markdown report (human-readable)
   def generate_markdown_report(results: list[EvaluationResult]) -> str:
       # Generate tables comparing AOrchestra vs baselines
       pass
   ```

4. **Benchmark runner**
   ```python
   class BenchmarkRunner:
       def __init__(self, tasks: list[BenchmarkTask], baselines: list[str]):
           self.tasks = tasks
           self.baselines = baselines  # ["aorchestra", "single_agent", "static_roles"]
       async def run_all(self) -> dict[str, list[EvaluationResult]]:
           results = {}
           for baseline in self.baselines:
               results[baseline] = []
               for task in self.tasks:
                   result = await self.run_benchmark(task, baseline)
                   results[baseline].append(result)
           return results
   ```

### Benchmark Task Categories

Based on available tools and capabilities, benchmark tasks should span:

1. **Math Tasks** (3-4 tasks)
   - Simple arithmetic (CalculatorTool)
   - Multi-step calculations
   - Mathematical reasoning
   - Difficulty: easy, medium, hard

2. **Code Tasks** (3-4 tasks)
   - Simple Python execution (CodeExecuteTool)
   - Code debugging
   - Code generation
   - Difficulty: easy, medium, hard

3. **Research Tasks** (2-3 tasks)
   - Information retrieval (WebSearchMockTool)
   - Synthesis from multiple sources
   - Question answering
   - Difficulty: easy, medium

4. **Planning Tasks** (2-3 tasks)
   - File-based tasks (FileReadTool)
   - Multi-step planning
   - Tool coordination
   - Difficulty: medium, hard

**Total: 10+ diverse tasks**

### Metrics to Track

From item.json and existing infrastructure:

1. **Accuracy** (scoring result)
   - Exact match: 0.0 or 1.0
   - LLM-as-judge: 0.0 to 1.0 (continuous)

2. **Cost** (USD)
   - Total cost per benchmark (OrchestratorState.total_cost_usd)
   - Model breakdown (model_breakdown from get_cost_summary())
   - Average cost per task

3. **Latency** (seconds)
   - Time from start to finish of run()
   - Measure in benchmark runner

4. **Token Usage**
   - Total tokens (get_total_tokens())
   - Prompt vs completion breakdown
   - Per-model breakdown

5. **Delegation Count**
   - Number of delegations (OrchestratorState.history length)
   - Indicates orchestration complexity

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| **Benchmark tasks too easy/hard** | High | Task difficulty may skew results. Pilot test tasks before full evaluation. Adjust expected answers and difficulty ratings. Include diverse difficulty levels. |
| **LLM-as-judge inconsistency** | High | LLM evaluation may be non-deterministic. Use consistent prompts and temperature=0. Run multiple evaluations per task and average. Document scoring rubric. |
| **Baseline implementation complexity** | Medium | Single-agent baseline is straightforward, but static-roles baseline may be complex. Keep static-roles simple (fixed roles, LLM for selection). Reuse existing Orchestrator patterns. |
| **Cost of running benchmarks** | Medium | Real LLM calls cost money. Use mock LLMs for development testing. Document expected costs. Add budget limits. |
| **Environment configuration errors** | Medium | ZAI_API_KEY, cost rates, lambda parameter may be misconfigured. Validate configuration at startup. Provide clear error messages. Use sensible defaults. |
| **Report format requirements** | Medium | Denario pipeline may have specific JSON schema requirements. Contact Denario team for requirements. Validate JSON schema before final reports. Keep schema flexible. |
| **Benchmark reproducibility** | High | Results may not be reproducible due to LLM randomness. Set temperature=0 for deterministic baselines. Document seed values. Use fixed prompts. |
| **Scoring fairness** | Medium | Exact match may be too strict for some tasks. Use normalized comparison (case-insensitive, whitespace). Allow partial credit via LLM-as-judge. |
| **Performance measurement noise** | Low | Latency measurements may be affected by system load. Run multiple trials and average. Measure wall-clock time vs CPU time. Document measurement method. |
| **Token usage tracking errors** | Low | OpenAI API may not return usage data. Handle None in CostRecord.from_openai_usage(). Fall back to token estimation. Log missing usage data. |
| **Cost rate accuracy** | Medium | Cost rates are estimates, not actual Z.ai pricing. Document that costs are estimates. Update rates when actual pricing available. Allow custom rates via COST_RATES. |
| **Model availability** | Medium | Premium model (glm-4-plus) may not be available. Implement graceful fallback to standard tier. Validate model availability at startup. Document model requirements. |
| **Tool failures in benchmarks** | Medium | Tools may fail during benchmark execution. Catch and log tool errors. Don't fail entire benchmark. Include error logs in results. |
| **Timeout handling** | Medium | Benchmarks may hang or take too long. Implement timeout per benchmark. Record timeouts as failures. Use asyncio.wait_for() for timeout. |
| **Result aggregation bugs** | Low | Aggregating metrics across runs may have errors. Test aggregation with sample data. Validate report calculations. Use type hints and Pydantic validation. |

## Recommended Approach

### High-Level Strategy

Implement evaluation harness in phases, building from simple benchmarks to comprehensive comparison:

**Phase 1: Benchmark Task Definition**
1. Create BenchmarkTask Pydantic model (id, name, category, goal, expected_answer, tools, scoring_method, difficulty)
2. Define 10+ benchmark tasks across 4 categories (math, code, research, planning)
3. Create task registry to load and validate tasks
4. Write unit tests for task validation
5. **Verification**: All tasks validate correctly, categories diverse

**Phase 2: Baseline Implementations**
1. Implement SingleAgentBaseline
   - Uses AgentFactory to create single agent with all tools
   - Solves goal by direct execution (no delegation)
2. Implement StaticRolesBaseline
   - Creates fixed sub-agents: math_agent, code_agent, research_agent, planning_agent
   - Uses simple LLM call to select agent type
   - Delegates to selected agent
3. Write unit tests for baseline execution
4. **Verification**: Baselines execute, return answers, track costs

**Phase 3: Scoring Mechanisms**
1. Implement exact_match scoring
   - Normalize strings (strip, lowercase)
   - Compare with expected_answer
   - Return 0.0 or 1.0
2. Implement llm_judge scoring
   - Use OpenAI client for evaluation
   - Prompt LLM to score answer quality (0.0-1.0)
   - Parse score from response
3. Write tests for scoring functions
4. **Verification**: Scoring produces correct results for sample cases

**Phase 4: Evaluation Harness**
1. Create EvaluationResult Pydantic model
2. Create BenchmarkRunner class
   - Initialize with tasks, baselines, orchestrator configuration
   - run_all() executes all benchmarks across all baselines
   - Track metrics: accuracy, cost, latency, tokens, delegations
   - Handle timeouts and errors gracefully
3. Integrate cost tracking from CostTracker and OrchestratorState
4. Write integration tests with mock LLMs
5. **Verification**: Runner executes benchmarks, captures metrics

**Phase 5: Report Generation**
1. Implement generate_json_report()
   - Serialize results to JSON
   - Include all metrics
   - Validate schema for Denario pipeline
2. Implement generate_markdown_report()
   - Create summary tables (accuracy, cost, latency per baseline)
   - Generate per-task breakdown
   - Highlight AOrchestra advantages
3. Write tests for report generation
4. **Verification**: JSON is valid, markdown renders correctly

**Phase 6: End-to-End Evaluation**
1. Create evaluation script (CLI entry point)
2. Run full benchmark suite with real LLMs
3. Generate JSON and markdown reports
4. Verify results are reasonable
5. Document expected costs and runtime
6. **Verification**: Full evaluation runs, produces reports

### Architectural Decisions

1. **Package Structure:**
   ```
   aorchestra/
   ├── evaluation/
   │   ├── __init__.py
   │   ├── tasks.py          # BenchmarkTask, task definitions, task registry
   │   ├── baselines.py      # SingleAgentBaseline, StaticRolesBaseline
   │   ├── scoring.py        # exact_match, llm_judge scoring
   │   ├── runner.py         # BenchmarkRunner, EvaluationResult
   │   ├── reports.py        # generate_json_report, generate_markdown_report
   │   └── config.py        # evaluation configuration
   └── scripts/
       └── run_evaluation.py # CLI entry point for running benchmarks
   ```

2. **Benchmark Task Model:**
   ```python
   class BenchmarkTask(BaseModel):
       id: str = Field(..., description="Unique task identifier")
       name: str = Field(..., description="Human-readable task name")
       category: Literal["math", "code", "research", "planning"] = Field(
           ..., description="Task category"
       )
       goal: str = Field(..., description="Task goal/goal string")
       expected_answer: Optional[str] = Field(
           None, description="Expected answer for exact_match scoring"
       )
       tools: list[str] = Field(
           default_factory=list,
           description="Tool names to make available"
       )
       scoring_method: Literal["exact_match", "llm_judge"] = Field(
           ..., description="How to score this task"
       )
       difficulty: Literal["easy", "medium", "hard"] = Field(
           ..., description="Task difficulty level"
       )
   ```

3. **Evaluation Result Model:**
   ```python
   class EvaluationResult(BaseModel):
       task_id: str
       task_name: str
       system: Literal["aorchestra", "single_agent", "static_roles"]
       answer: str
       score: float  # 0.0 to 1.0
       cost_usd: float
       latency_seconds: float
       total_tokens: int
       delegation_count: int
       model_breakdown: dict[str, dict[str, float | int]]
       error: Optional[str] = None  # If benchmark failed
   ```

4. **Baseline Implementations:**

   **SingleAgentBaseline:**
   ```python
   class SingleAgentBaseline:
       def __init__(self, model: ModelConfig, tools: list):
           self.model = model
           self.tools = tools
           self.factory = AgentFactory()

       async def solve(self, goal: str) -> tuple[str, CostRecord]:
           tuple_def = AgentTuple(
               instruction=goal,
               context="",
               tools=self.tools,
               model=self.model,
           )
           agent = self.factory.create(tuple_def)
           observation, cost_record = await agent.execute()
           return observation.result_summary, cost_record
   ```

   **StaticRolesBaseline:**
   ```python
   class StaticRolesBaseline:
       def __init__(self, model: ModelConfig, tool_registry: ToolRegistry):
           self.model = model
           self.tool_registry = tool_registry
           self.agents = self._create_fixed_agents()

       def _create_fixed_agents(self) -> dict[str, SubAgent]:
           return {
               "math": SubAgent(AgentTuple(..., tools=[CalculatorTool()], ...)),
               "code": SubAgent(AgentTuple(..., tools=[CodeExecuteTool()], ...)),
               "research": SubAgent(AgentTuple(..., tools=[WebSearchMockTool()], ...)),
               "planning": SubAgent(AgentTuple(..., tools=[FileReadTool()], ...)),
           }

       async def solve(self, goal: str) -> tuple[str, CostRecord]:
           # LLM call to select agent type
           agent_type = await self._select_agent_type(goal)
           agent = self.agents[agent_type]
           observation, cost_record = await agent.execute()
           return observation.result_summary, cost_record
   ```

5. **Scoring Functions:**
   ```python
   def score_exact_match(actual: str, expected: str) -> float:
       normalized_actual = actual.strip().lower()
       normalized_expected = expected.strip().lower()
       return 1.0 if normalized_actual == normalized_expected else 0.0

   async def score_llm_judge(
       goal: str,
       answer: str,
       client: AsyncOpenAI,
       model: str = "glm-4.7"
   ) -> float:
       prompt = (
           f"Rate the quality of this answer on a scale of 0.0 to 1.0.\n\n"
           f"Task: {goal}\n\n"
           f"Answer: {answer}\n\n"
           f"Respond with only a single number (0.0 to 1.0)."
       )
       response = await client.chat.completions.create(
           model=model,
           messages=[{"role": "user", "content": prompt}],
           temperature=0.0,
       )
       try:
           return float(response.choices[0].message.content.strip())
       except ValueError:
           return 0.5  # Default score on parse failure
   ```

6. **Benchmark Runner:**
   ```python
   class BenchmarkRunner:
       def __init__(
           self,
           tasks: list[BenchmarkTask],
           model: ModelConfig,
           lambda_param: float = 0.5,
           run_parallel: bool = True
       ):
           self.tasks = tasks
           self.model = model
           self.lambda_param = lambda_param
           self.run_parallel = run_parallel
           self.results: dict[str, list[EvaluationResult]] = {}

       async def run_all(self) -> dict[str, list[EvaluationResult]]:
           baselines = ["aorchestra", "single_agent", "static_roles"]

           for baseline in baselines:
               self.results[baseline] = []
               for task in self.tasks:
                   result = await self._run_benchmark(task, baseline)
                   self.results[baseline].append(result)

           return self.results

       async def _run_benchmark(
           self,
           task: BenchmarkTask,
           baseline: str
       ) -> EvaluationResult:
           start_time = time.time()

           try:
               # Execute baseline
               if baseline == "aorchestra":
                   answer, metrics = await self._run_aorchestra(task)
               elif baseline == "single_agent":
                   answer, metrics = await self._run_single_agent(task)
               else:  # static_roles
                   answer, metrics = await self._run_static_roles(task)

               # Score answer
               if task.scoring_method == "exact_match":
                   score = score_exact_match(answer, task.expected_answer)
               else:  # llm_judge
                   score = await score_llm_judge(task.goal, answer)

               latency = time.time() - start_time

               return EvaluationResult(
                   task_id=task.id,
                   task_name=task.name,
                   system=baseline,
                   answer=answer,
                   score=score,
                   latency_seconds=latency,
                   **metrics,
               )
           except Exception as e:
               return EvaluationResult(
                   task_id=task.id,
                   task_name=task.name,
                   system=baseline,
                   answer="",
                   score=0.0,
                   latency_seconds=time.time() - start_time,
                   error=str(e),
               )
   ```

7. **Report Generation:**
   ```python
   def generate_json_report(
       results: dict[str, list[EvaluationResult]]
   ) -> str:
       data = {
           "metadata": {
               "timestamp": datetime.utcnow().isoformat(),
               "num_tasks": len(next(iter(results.values()))),
               "baselines": list(results.keys()),
           },
           "results": {
               baseline: [r.model_dump() for r in baseline_results]
               for baseline, baseline_results in results.items()
           },
           "summary": _calculate_summary(results),
       }
       return json.dumps(data, indent=2)

   def generate_markdown_report(
       results: dict[str, list[EvaluationResult]]
   ) -> str:
       lines = []
       lines.append("# AOrchestra Evaluation Report")
       lines.append("")
       lines.append("## Summary")
       lines.append("")
       # Generate summary table
       lines.append("| System | Accuracy | Avg Cost ($USD) | Avg Latency (s) |")
       lines.append("|--------|----------|----------------|------------------|")
       for baseline, baseline_results in results.items():
           accuracy = sum(r.score for r in baseline_results) / len(baseline_results)
           avg_cost = sum(r.cost_usd for r in baseline_results) / len(baseline_results)
           avg_latency = sum(r.latency_seconds for r in baseline_results) / len(baseline_results)
           lines.append(f"| {baseline} | {accuracy:.2%} | ${avg_cost:.4f} | {avg_latency:.2f} |")
       lines.append("")
       # Per-task breakdown
       lines.append("## Per-Task Results")
       lines.append("")
       for task in results["aorchestra"]:
           lines.append(f"### {task.task_name}")
           lines.append("")
           lines.append(f"**Category:** {task.task_id.split('-')[0]}")
           lines.append(f"**Difficulty:** {task.difficulty}")
           lines.append("")
           lines.append("| System | Score | Cost ($) | Latency (s) |")
           lines.append("|--------|-------|----------|-------------|")
           for baseline, baseline_results in results.items():
               result = next(r for r in baseline_results if r.task_id == task.task_id)
               lines.append(f"| {baseline} | {result.score:.2f} | ${result.cost_usd:.4f} | {result.latency_seconds:.2f} |")
           lines.append("")
       return "\n".join(lines)
   ```

### Benchmark Task Definitions

**Proposed 12 benchmark tasks (4 categories × 3 difficulty levels):**

**Math Tasks (4 tasks):**
1. `math-001-easy-addition`: "Add 42 and 78"
   - Tools: [calculator]
   - Expected: "120"
   - Scoring: exact_match

2. `math-002-medium-multiplication`: "Multiply 23 by 17, then add 15"
   - Tools: [calculator]
   - Expected: "406"
   - Scoring: exact_match

3. `math-003-medium-division-chain`: "Divide 1000 by 8, then divide the result by 5"
   - Tools: [calculator]
   - Expected: "25"
   - Scoring: exact_match

4. `math-004-hard-arithmetic-chain`: "Calculate: (45 * 12) - (156 / 4) + (23 * 7)"
   - Tools: [calculator]
   - Expected: "662"
   - Scoring: exact_match

**Code Tasks (4 tasks):**
5. `code-001-easy-hello-world`: "Write a Python program that prints 'Hello, World!'"
   - Tools: [code_execute]
   - Expected: Contains "Hello, World!"
   - Scoring: exact_match (substring)

6. `code-002-medium-sum-list`: "Write Python code to calculate the sum of numbers from 1 to 100"
   - Tools: [code_execute]
   - Expected: "5050"
   - Scoring: exact_match

7. `code-003-medium-fibonacci`: "Write Python code to generate the first 10 Fibonacci numbers"
   - Tools: [code_execute]
   - Expected: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
   - Scoring: llm_judge

8. `code-004-hard-quadratic`: "Write Python code to solve the quadratic equation x^2 - 5x + 6 = 0"
   - Tools: [code_execute]
   - Expected: Roots at x=2 and x=3
   - Scoring: llm_judge

**Research Tasks (2 tasks):**
9. `research-001-easy-python-info`: "Search for information about Python programming language"
   - Tools: [web_search_mock]
   - Scoring: llm_judge

10. `research-002-medium-async-info`: "Find information about Python asyncio library"
    - Tools: [web_search_mock]
    - Scoring: llm_judge

**Planning Tasks (2 tasks):**
11. `planning-001-medium-file-analysis`: "Read the file 'data.txt' and summarize its contents"
    - Tools: [file_read]
    - Expected: Summarized content
    - Scoring: llm_judge

12. `planning-002-hard-multi-step`: "Calculate the area of a rectangle (15 × 23), then create a text file with the result"
    - Tools: [calculator, file_read, file_write (if available)]
    - Expected: File created with "345"
    - Scoring: llm_judge

**Note:** Task definitions should be in a separate file (evaluation/tasks.py) for easy modification.

### Implementation Order

Priority order based on dependencies and complexity:

1. **Task definitions and models** (evaluation/tasks.py)
   - No dependencies, foundational
   - Define 10+ benchmark tasks

2. **Baseline implementations** (evaluation/baselines.py)
   - Depends on tasks, factory
   - SingleAgentBaseline first (simpler), then StaticRolesBaseline

3. **Scoring mechanisms** (evaluation/scoring.py)
   - Independent of baselines
   - exact_match first (simpler), then llm_judge

4. **Benchmark runner** (evaluation/runner.py)
   - Depends on tasks, baselines, scoring
   - Core evaluation logic

5. **Report generation** (evaluation/reports.py)
   - Depends on runner results
   - JSON first (simpler), then markdown

6. **CLI script** (scripts/run_evaluation.py)
   - Depends on runner, reports
   - User-facing entry point

### Testing Strategy

Follow existing test patterns:

1. **Unit Tests:**
   - Test task validation (task_registry)
   - Test scoring functions (exact_match, llm_judge with mock)
   - Test baseline execution with mocked LLMs
   - Test report generation

2. **Integration Tests:**
   - Test runner with mock benchmarks
   - Test cost tracking across runs
   - Test timeout handling

3. **End-to-End Tests (optional):**
   - Run full evaluation with real LLMs
   - Verify report generation
   - (Requires API keys, may be slow)

4. **Test Fixtures:**
   - mock_openai_response (from conftest.py)
   - sample_benchmark_tasks
   - sample_evaluation_results

## Open Questions

1. **Denario pipeline JSON schema** - What is the exact schema required for the Denario paper generation pipeline?
   - Clarification needed from Denario team
   - For now, use flexible JSON with metadata, results, summary

2. **LLM-as-judge rubric** - What specific criteria should the LLM judge evaluate?
   - Accuracy, completeness, conciseness?
   - Should provide detailed prompt template
   - Default: rate overall answer quality (0.0-1.0)

3. **Static-roles baseline complexity** - How sophisticated should the static roles baseline be?
   - Option A: Simple keyword-based agent selection (e.g., "calculate" → math_agent)
   - Option B: LLM-based agent selection (more realistic, but adds cost)
   - Recommended: Option B with LLM selection (fairer comparison)

4. **Benchmark task difficulty calibration** - How to ensure tasks are appropriately rated (easy/medium/hard)?
   - Pilot testing required
   - Adjust difficulty based on baseline performance
   - Target: Single-agent baseline ~50% accuracy on medium tasks

5. **Number of evaluation trials** - Should each benchmark be run multiple times to average variability?
   - Trade-off: More trials = more reliable results, but higher cost and time
   - Recommended: 3 trials per benchmark, average results
   - Document trial count in reports

6. **Budget constraints** - What is the budget limit for running full evaluation?
   - Real LLM calls cost money
   - Should implement budget limit in runner
   - Document expected total cost

7. **Timeout values** - What should the timeout be per benchmark?
   - Depends on task complexity and model speed
   - Recommended: 60 seconds for easy/medium, 120 seconds for hard
   - Make configurable

8. **File-based benchmarks** - Should planning tasks create real files or use mocks?
   - WebSearchMockTool already uses mock data
   - Should create similar FileWriteMockTool for file-based tasks
   - Avoid side effects on user's filesystem

9. **Reproducibility** - How to ensure benchmarks are reproducible?
   - Set temperature=0 for baselines
   - Use fixed random seeds if applicable
   - Document LLM model versions
   - Store benchmark results with timestamps

10. **Success criteria thresholds** - What are the target metrics for AOrchestra?
    - Accuracy: Should AOrchestra beat baselines by what margin?
    - Cost: Should AOrchestra be within what cost factor?
    - Define success thresholds (e.g., AOrchestra > 80% accuracy, < 2× cost of single-agent)
