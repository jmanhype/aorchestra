# Research: Cost-aware model routing

**Date**: 2025-02-04
**Item**: 004-cost-aware-model-routing

## Research Question

Implement model selection strategy where the orchestrator picks cheap models for simple subtasks and expensive models for complex ones. Define a CostTracker monitoring token usage and monetary cost. Include a ModelRegistry with 3+ tiers.

## Summary

Item 004 implements **cost-aware model routing** to optimize the trade-off between task accuracy and monetary cost. Currently, the orchestrator uses a single model (configured at initialization) for all delegations, regardless of task complexity. This is inefficient because simple subtasks could use cheaper models while complex tasks require more capable (and expensive) ones.

The foundation (items 001-003) is complete with full implementations of AgentTuple, SubAgent, Observation, AgentFactory, Orchestrator, and ToolRegistry. The ModelConfig class exists but is a simple data structure without tier management or cost tracking. Token usage information from OpenAI API responses is available but not being captured or tracked.

Key implementation requirements:
1. **ModelRegistry** - A centralized registry managing model configurations with 3+ tiers (flash/cheap, standard, premium)
2. **CostTracker** - A component monitoring token usage (prompt_tokens, completion_tokens) and estimated monetary cost per delegation
3. **Model selection strategy** - Heuristics or LLM-based logic to determine task complexity and select appropriate model tier
4. **Lambda parameter** - A configurable cost-performance trade-off parameter controlling how aggressively to optimize for cost vs accuracy
5. **Integration with Orchestrator** - Replace hardcoded model selection in `_delegate()` with ModelRegistry-based selection
6. **Token usage extraction** - Capture and track usage from OpenAI API responses

The implementation must follow the existing registry pattern from ToolRegistry (item 003) and integrate seamlessly with ModelConfig and the Orchestrator class.

## Current State Analysis

### Existing Implementation

**Items 001-003 are complete and production-ready** - all core infrastructure exists:

- **aorchestra/models/config.py:1-57** - ModelConfig dataclass
  - Lines 12-36: Pydantic dataclass with name, api_base, api_key, temperature, max_tokens
  - Lines 17: Comment indicates models like 'glm-4.7', 'glm-4-flash' are supported
  - Lines 47-51: `to_openai_kwargs()` for client initialization
  - No tier information, no cost data, no model selection logic

- **aorchestra/core/agents.py:14-45** - SubAgent with LLM calling
  - Lines 14: Imports AsyncOpenAI from openai library
  - Lines 30-45: Lazy-initialized OpenAI client property
  - Lines 105-135: `_call_llm()` method makes API calls with model name
  - Line 135: Passes `max_tokens` parameter to API call
  - **NO token usage tracking** - response is used but usage metadata is not extracted

- **aorchestra/core/agents.py:155-156** - Response processing
  - Line 155: `choice = response.choices[0]`
  - **Missing**: No extraction of `response.usage` which contains prompt_tokens, completion_tokens, total_tokens

- **aorchestra/core/agents.py:126-128** - LLM call parameters
  - Lines 126-135: Uses `self.tuple.model.name`, `temperature`, `max_tokens`
  - No cost tracking mechanism

- **aorchestra/core/orchestrator.py:199-312** - Orchestrator delegation
  - Lines 36-40: Orchestrator initialized with a single ModelConfig
  - Line 211: `model=self.model,` - **Hardcoded model selection** - uses same model for all delegations
  - Lines 199-215: `_delegate()` method creates AgentTuple with fixed model
  - **No complexity analysis or model selection logic**

- **aorchestra/core/orchestrator.py:50-53** - Orchestrator initialization
  - Line 53: `self.client = AsyncOpenAI(**model.to_openai_kwargs())`
  - Uses single model for orchestrator's own decisions
  - Line 50: Receives ModelConfig as constructor parameter

- **aorchestra/orchestrator/actions.py:12-31** - DelegateAction model
  - Lines 21-23: Includes `tools: list[str]` for tool selection
  - **Missing**: No `model` or `model_tier` field - orchestrator cannot request specific model per subtask

- **aorchestra/orchestrator/state.py:1-76** - OrchestratorState and Delegation
  - Lines 16-46: Delegation model with step, tuple, observation, timestamp
  - Lines 48-76: OrchestratorState with goal, step, history, max_steps
  - **Missing**: No cost tracking fields (total_tokens, estimated_cost)
  - No per-delegation cost information

- **aorchestra/core/observations.py:1-43** - Observation model
  - Lines 13-33: result_summary, artifacts, error_logs
  - **Missing**: No token usage or cost metadata
  - Could be extended with `token_usage` field

### Current Patterns and Conventions

**Established patterns from items 001-003:**

1. **Registry pattern** (from item 003):
   - ToolRegistry manages tools with metadata (tools/registry.py:52-174)
   - Pydantic models for metadata (ToolMetadata, ToolSelectionCriteria)
   - Registration with validation (registry.py:68-88)
   - Selection based on criteria (registry.py:149-174)
   - **ModelRegistry should follow this pattern**

2. **Pydantic for all data models** - ModelConfig, Observation, Delegation all use Pydantic
   - ModelConfig uses Field with descriptions (models/config.py:12-36)
   - Enables validation and serialization
   - ModelMetadata and ModelTier should use Pydantic

3. **Factory pattern** - AgentFactory creates SubAgents (factory.py:18-36)
   - Validates tuples before instantiation
   - Could potentially integrate with ModelRegistry

4. **Async-first design** - All LLM calls are async
   - SubAgent.execute() is async (agents.py:36)
   - Orchestrator._delegate() is async (orchestrator.py:177)
   - Cost tracking must work with async execution

5. **Mock-based testing** - Comprehensive test coverage with mocks
   - tests/test_agents.py:48-48 mocks OpenAI responses
   - tests/test_orchestrator.py uses mocked LLM calls
   - Cost tracking tests must mock usage data

6. **Error handling** - Errors captured in Observation.error_logs
   - Tool errors don't raise, get logged
   - Cost tracking errors should be captured similarly

### Integration Points

**Item 004 must integrate with:**

1. **ModelConfig** (models/config.py) - Current simple structure
   - Need to extend or create new ModelMetadata with cost info
   - Could add optional cost fields to existing ModelConfig
   - Or create separate ModelTier/ModelMetadata classes

2. **Orchestrator._delegate()** (orchestrator.py:199-215)
   - Line 211: `model=self.model` must be replaced with dynamic selection
   - Must analyze task complexity
   - Must select model from ModelRegistry based on complexity + lambda parameter

3. **SubAgent._call_llm()** (agents.py:105-135)
   - Line 135: Currently calls LLM without tracking usage
   - Must extract `response.usage` after API call
   - Must capture prompt_tokens, completion_tokens
   - Must return or store usage information

4. **Observation** (observations.py:13-33)
   - Currently has result_summary, artifacts, error_logs
   - Should be extended with token_usage field
   - Or cost tracking can be separate from Observation

5. **Delegation** (orchestrator/state.py:16-46)
   - Currently tracks tuple, observation, step, timestamp
   - Should track cost per delegation
   - Enables total cost calculation across all delegations

6. **OrchestratorState** (orchestrator/state.py:48-76)
   - Should track total cost across all delegations
   - Provide cost summary methods

7. **DelegateAction** (orchestrator/actions.py:12-31)
   - Currently has instruction, context, tools, reasoning
   - May need to include model_tier or complexity_score
   - Or model selection happens entirely in orchestrator

**Downstream dependencies:**

- **Item 005** (evaluation) - Will use cost metrics for benchmark comparison
- Future cost optimization features

## Key Files

### Core Dependencies (Items 001-003)

- **aorchestra/models/config.py:1-57** - ModelConfig structure
  - Current simple model configuration (name, api_base, temperature, max_tokens)
  - Line 17: Supports 'glm-4.7', 'glm-4-flash' models
  - Line 47-51: to_openai_kwargs() for client initialization
  - **Must extend** with cost information or use as base for ModelTier

- **aorchestra/core/agents.py:14-45** - SubAgent with LLM integration
  - Lines 30-45: OpenAI client lazy initialization
  - Lines 105-135: `_call_llm()` - main API call point
  - **Line 155**: Response processing - ideal place to extract usage
  - **Missing**: No extraction of `response.usage`
  - Must be modified to return or track token usage

- **aorchestra/core/orchestrator.py:36-215** - Orchestrator delegation
  - Lines 36-40: Single ModelConfig in constructor
  - Lines 199-215: `_delegate()` method
  - **Line 211**: `model=self.model` - hardcoded model selection
  - **Must replace** with ModelRegistry-based selection
  - Should analyze task complexity before model selection

- **aorchestra/orchestrator/actions.py:12-31** - DelegateAction
  - Lines 12-31: Pydantic model with instruction, context, tools, reasoning
  - **May need extension**: Add model_tier field
  - Or orchestrator makes model decision independently

- **aorchestra/orchestrator/state.py:1-76** - State models
  - Lines 16-46: Delegation record
  - Lines 48-76: OrchestratorState
  - **Missing**: Cost tracking fields
  - Should add: token_usage, estimated_cost per delegation
  - OrchestratorState should track total_cost

- **aorchestra/core/observations.py:1-43** - Observation model
  - Lines 13-33: result_summary, artifacts, error_logs
  - **May need extension**: Add token_usage field
  - Or create separate CostRecord

### Reference Pattern from Item 003

- **aorchestra/tools/registry.py:52-174** - ToolRegistry pattern
  - Lines 52-88: ToolRegistry.__init__() and register()
  - Lines 112-122: get(), get_all() methods
  - Lines 149-174: select_tools() with criteria matching
  - **ModelRegistry should follow this structure**

- **aorchestra/tools/registry.py:12-47** - ToolMetadata and ToolSelectionCriteria
  - Lines 12-32: ToolMetadata with tags, capabilities
  - Lines 35-47: ToolSelectionCriteria
  - **ModelTier and ModelSelectionCriteria should use similar pattern**

- **aorchestra/tools/registry.py:90-108** - Validation logic
  - Lines 90-108: Validation in register()
  - ModelRegistry should validate model configs

- **aorchestra/tools/builtins.py:175-225** - get_builtin_tools_metadata()
  - Pattern for registering pre-configured items
  - ModelRegistry should have similar get_builtin_models()

### Test Files (Patterns to Follow)

- **tests/test_models.py:1-57** - ModelConfig testing
  - Tests for validation, field defaults
  - Tests for to_openai_kwargs()
  - Similar tests needed for ModelTier, ModelRegistry

- **tests/test_agents.py:48-48** - LLM response mocking
  - Lines 48-48: Creates mock OpenAI response
  - **Must extend** to mock usage data in tests
  - Pattern: add `mock_response.usage = mock.MagicMock(prompt_tokens=100, completion_tokens=50)`

- **tests/test_orchestrator.py:98-121** - Delegation testing
  - Tests for _delegate() creating tuples
  - Should verify model selection logic
  - Should verify cost tracking

- **tests/test_tool_registry.py** - ToolRegistry tests (exists)
  - Registry testing patterns
  - Should follow similar patterns for ModelRegistry tests

### Configuration

- **aorchestra/config.py:12-25** - Config management
  - Lines 22-24: Loads ZAI_MODEL from environment
  - Current default: "glm-4.7"
  - May need to load cost rates or model tiers

- **.env.example:1-6** - Environment variables
  - Lines 4-6: ZAI_API_KEY, ZAI_API_BASE, ZAI_MODEL
  - May need to add: COST_RATES (JSON), DEFAULT_LAMBDA

## Technical Considerations

### Dependencies

**External Dependencies (already installed):**

1. **pydantic>=2.0** - For ModelTier, ModelMetadata, CostTracker models
   - Used extensively in codebase
   - Essential for cost tracking data structures

2. **openai>=1.0** - For API usage tracking
   - Response objects include `.usage` attribute
   - Has prompt_tokens, completion_tokens, total_tokens
   - No new installation needed

3. **typing** - For type hints
   - Standard library

**Internal Dependencies (from items 001-003):**

1. **ModelConfig** (models/config.py)
   - Base structure for model configuration
   - May be extended or used as component in ModelTier

2. **Orchestrator** (core/orchestrator.py)
   - Must be modified to use ModelRegistry
   - Line 211 must be changed from hardcoded to dynamic selection

3. **SubAgent** (core/agents.py)
   - Must extract token usage from API responses
   - Must return usage information to Orchestrator

4. **Observation/Delegation** (orchestrator/state.py, core/observations.py)
   - May need extension to include cost information

5. **ToolRegistry pattern** (tools/registry.py)
   - Reference implementation for registry pattern
   - ModelRegistry should follow similar structure

### Patterns to Follow

**From items 001-003:**

1. **Registry pattern** (from ToolRegistry)
   ```python
   class ModelRegistry:
       def __init__(self):
           self._models: dict[str, ModelConfig] = {}
           self._metadata: dict[str, ModelTier] = {}

       def register(self, model: ModelConfig, metadata: ModelTier) -> None:
           # Validate and store
           pass

       def select_model(self, criteria: ModelSelectionCriteria) -> ModelConfig:
           # Select based on tier, complexity, lambda
           pass
   ```

2. **Pydantic models for metadata**
   ```python
   class ModelTier(BaseModel):
       name: str
       description: str
       tier: Literal["flash", "standard", "premium"]
       cost_per_1k_tokens: float
       capabilities: list[str] = Field(default_factory=list)
   ```

3. **Cost tracking**
   ```python
   class CostRecord(BaseModel):
       prompt_tokens: int
       completion_tokens: int
       total_tokens: int
       estimated_cost: float  # USD
       model_name: str
   ```

4. **Complexity heuristics**
   ```python
   def estimate_complexity(instruction: str, context: str, tools: list[str]) -> float:
       # Analyze instruction length, context size, tool complexity
       # Return complexity score (0.0 to 1.0)
       pass
   ```

5. **Model selection with lambda**
   ```python
   def select_model(complexity: float, lambda_param: float) -> str:
       # Higher lambda = prefer cheaper models
       # Higher complexity = need better model
       pass
   ```

**New patterns for item 004:**

1. **Token usage extraction**
   ```python
   # After LLM call in SubAgent
   usage = response.usage
   prompt_tokens = usage.prompt_tokens
   completion_tokens = usage.completion_tokens
   ```

2. **Cost calculation**
   ```python
   def calculate_cost(tokens: int, cost_per_1k: float) -> float:
       return (tokens / 1000) * cost_per_1k
   ```

3. **Model selection strategy**
   ```python
   # Analyze instruction complexity
   complexity = estimate_complexity(instruction, context, tools)

   # Apply lambda threshold
   if lambda_param > 0.7 and complexity < 0.3:
       return get_model_by_tier("flash")
   elif complexity > 0.7:
       return get_model_by_tier("premium")
   else:
       return get_model_by_tier("standard")
   ```

4. **Cost aggregation**
   ```python
   class OrchestratorState:
       total_tokens: int = 0
       total_cost: float = 0.0

       def add_delegation(self, delegation: Delegation, cost_record: CostRecord):
           self.history.append(delegation)
           self.total_tokens += cost_record.total_tokens
           self.total_cost += cost_record.estimated_cost
   ```

### Model Tier Definitions

Based on item.json requirement for "at least 3 model tiers (flash, standard, premium)":

**Proposed tiers using Z.ai models:**

1. **Flash tier (cheap):**
   - Model: `glm-4-flash` (fast, cost-effective)
   - Use cases: Simple calculations, data formatting, basic text processing
   - Cost: ~$0.0001 per 1K tokens (estimated)

2. **Standard tier (balanced):**
   - Model: `glm-4.7` (current default)
   - Use cases: General reasoning, moderate complexity tasks
   - Cost: ~$0.001 per 1K tokens (estimated)

3. **Premium tier (expensive):**
   - Model: `glm-4-plus` or similar high-end model (if available)
   - Use cases: Complex reasoning, code generation, multi-step planning
   - Cost: ~$0.01 per 1K tokens (estimated)

**Note**: Actual cost rates need to be obtained from Z.ai pricing documentation.

### Complexity Heuristics

**Factors to estimate task complexity:**

1. **Instruction length** - Longer instructions suggest complexity
2. **Context size** - More context information needed
3. **Tool complexity** - Certain tools (code_execute, web_search) indicate higher complexity
4. **Task type keywords** - Words like "analyze", "reason", "optimize" suggest complexity
5. **Historical performance** - Previous delegations with similar tasks

**Simple heuristic:**
```python
def estimate_complexity(instruction: str, tools: list[str], context_length: int) -> float:
    score = 0.0

    # Length factor (0-0.3)
    score += min(len(instruction) / 500, 0.3)

    # Tool complexity (0-0.4)
    complex_tools = ["code_execute", "web_search"]
    if any(t in complex_tools for t in tools):
        score += 0.4

    # Context size (0-0.3)
    score += min(context_length / 2000, 0.3)

    return min(score, 1.0)
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| **Inaccurate cost estimates** | High | Cost rates may not be publicly available for Z.ai models. Implement configurable cost rates. Allow users to override. Document that costs are estimates. |
| **Poor model selection decisions** | High | Heuristic complexity estimation may misclassify tasks. Start conservative (use standard model more often). Add logging of model selection decisions. Allow manual override via DelegateAction. |
| **Missing token usage data** | High | OpenAI API responses may not include usage in all cases. Handle None gracefully. Add fallback cost estimation based on input length. Log when usage data is unavailable. |
| **Increased latency** | Medium | Model selection logic adds overhead per delegation. Cache complexity scores for similar tasks. Keep heuristics simple and fast. |
| **Breaking changes to existing API** | Medium | Adding cost tracking may break existing tests. Keep changes backward compatible. Make cost tracking optional via feature flag. |
| **Lambda parameter tuning difficulty** | Medium | Finding optimal lambda value may require experimentation. Document recommended ranges (0.0-1.0). Start with lambda=0.5 (balanced). |
| **Token usage extraction bugs** | Medium | OpenAI response structure may vary. Add comprehensive error handling. Test with real API responses. Mock usage data in tests. |
| **Model tier availability** | Medium | Premium model may not be available on Z.ai. Implement graceful fallback to standard tier. Validate model availability at initialization. |
| **Cost tracking performance overhead** | Low | Tracking costs per delegation may add minimal overhead. Use efficient data structures. Aggregate costs periodically rather than per-token. |
| **Complex task misclassification** | High | Important tasks incorrectly classified as simple. Use higher threshold for premium selection. Consider using LLM for complexity estimation as fallback. |
| **Testing complexity** | Medium | Mocking token usage and costs adds test complexity. Create helper fixtures for cost data. Test both real and mocked scenarios. |
| **Observation serialization** | Low | Adding cost data to Observation may affect serialization. Use Pydantic for validation. Ensure JSON serialization works. |

## Recommended Approach

### High-Level Strategy

Implement cost-aware routing in phases, following the registry pattern from item 003:

**Phase 1: Model Registry and Tiers**
1. Create `ModelTier` Pydantic model (tier, cost_per_1k, capabilities)
2. Create `ModelMetadata` Pydantic model (name, tier, description, cost_rates)
3. Implement `ModelRegistry` class (register, get, get_by_tier, select_model)
4. Implement `ModelSelectionCriteria` model (complexity, lambda, tier_preference)
5. Create `get_builtin_models()` helper for default model tiers
6. Write unit tests for registry operations
7. **Verification**: Registry manages models correctly, selection works

**Phase 2: Cost Tracking**
1. Create `CostRecord` Pydantic model (prompt_tokens, completion_tokens, cost, model_name)
2. Create `CostTracker` class (track_delegation, get_total_cost, get_summary)
3. Modify `SubAgent._call_llm()` to extract token usage from response
4. Modify `SubAgent._execute_impl()` to return CostRecord alongside Observation
5. Update `AgentTuple` or `Delegation` to include cost information
6. Update `OrchestratorState` to track total cost
7. Write unit tests for cost tracking with mocked usage data
8. **Verification**: Token usage captured correctly, costs calculated accurately

**Phase 3: Model Selection Logic**
1. Implement `estimate_complexity()` function (analyze instruction, tools, context)
2. Implement `select_model_by_complexity()` function (apply lambda threshold)
3. Create `model_selection` module with heuristics
4. Write tests for complexity estimation
5. **Verification**: Complexity scores make sense, model selection works

**Phase 4: Orchestrator Integration**
1. Modify `Orchestrator.__init__()` to accept optional ModelRegistry
2. Initialize default ModelRegistry with builtin models if not provided
3. Modify `Orchestrator._delegate()` to:
   - Estimate complexity of subtask
   - Select model from ModelRegistry based on complexity + lambda
   - Pass selected model to AgentTuple (instead of `self.model`)
4. Update `Orchestrator._integrate_observation()` to track cost
5. Update `Delegation` to optionally include CostRecord
6. Update `OrchestratorState` to track total cost
7. Write integration tests with different lambda values
8. **Verification**: Orchestrator selects appropriate models per delegation

**Phase 5: Configuration and Tuning**
1. Add cost_rates to Config class or environment variables
2. Add lambda parameter to Orchestrator constructor
3. Document recommended lambda values and complexity thresholds
4. Create example showing cost-aware routing in action
5. Update .env.example with cost configuration
6. **Verification**: Configuration works, different lambda values affect model selection

**Phase 6: End-to-End Testing**
1. Create integration tests with real LLM (optional, requires API keys)
2. Test tasks with different complexity levels
3. Verify cheaper models used for simple tasks
4. Verify expensive models used for complex tasks
5. Verify cost tracking accuracy across multiple delegations
6. Test error handling (missing usage data, unavailable models)
7. **Verification**: Full cost-aware routing workflow functions correctly

### Architectural Decisions

1. **Package Structure:**
   ```
   aorchestra/
   ├── models/
   │   ├── config.py          # (existing) ModelConfig
   │   ├── registry.py        # (NEW) ModelRegistry, ModelTier, ModelMetadata
   │   └── cost.py            # (NEW) CostTracker, CostRecord, cost calculations
   ├── core/
   │   ├── agents.py          # (MODIFY) Extract usage from LLM responses
   │   ├── orchestrator.py    # (MODIFY) Use ModelRegistry for model selection
   │   └── factory.py         # (optional) May integrate with ModelRegistry
   ├── orchestrator/
   │   ├── state.py           # (MODIFY) Add cost tracking to OrchestratorState
   │   └── selection.py       # (NEW) Complexity estimation, model selection logic
   └── __init__.py            # Export ModelRegistry, CostTracker
   ```

2. **ModelTier Model:**
   ```python
   class ModelTier(BaseModel):
       tier: str  # "flash", "standard", "premium"
       model_name: str
       cost_per_1k_input: float
       cost_per_1k_output: float
       description: str
       capabilities: list[str] = Field(default_factory=list)
   ```

3. **ModelRegistry Class:**
   ```python
   class ModelRegistry:
       def __init__(self):
           self._tiers: dict[str, ModelTier] = {}
           self._by_tier: dict[str, list[ModelConfig]] = {
               "flash": [],
               "standard": [],
               "premium": [],
           }

       def register(self, model: ModelConfig, tier: str, cost_per_1k: float):
           pass

       def get_by_tier(self, tier: str) -> ModelConfig:
           pass

       def select_model(self, complexity: float, lambda_param: float) -> ModelConfig:
           # Higher lambda = prefer cheaper
           # Higher complexity = need better model
           pass
   ```

4. **CostRecord Model:**
   ```python
   class CostRecord(BaseModel):
       model_name: str
       prompt_tokens: int
       completion_tokens: int
       total_tokens: int
       estimated_cost: float
       timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
   ```

5. **CostTracker Class:**
   ```python
   class CostTracker:
       def __init__(self):
           self._records: list[CostRecord] = []

       def track(self, record: CostRecord):
           self._records.append(record)

       def get_total_cost(self) -> float:
           return sum(r.estimated_cost for r in self._records)

       def get_summary(self) -> dict:
           return {
               "total_cost": self.get_total_cost(),
               "total_tokens": sum(r.total_tokens for r in self._records),
               "delegations": len(self._records),
           }
   ```

6. **Complexity Estimation:**
   ```python
   def estimate_complexity(
       instruction: str,
       tools: list[str],
       context_length: int,
   ) -> float:
       score = 0.0

       # Instruction length (max 0.3)
       score += min(len(instruction) / 500, 0.3)

       # Tool complexity (max 0.4)
       complex_tools = ["code_execute", "web_search", "file_read"]
       if any(t in complex_tools for t in tools):
           score += 0.4

       # Context size (max 0.3)
       score += min(context_length / 2000, 0.3)

       return min(score, 1.0)
   ```

7. **Model Selection with Lambda:**
   ```python
   def select_model(complexity: float, lambda_param: float, registry: ModelRegistry) -> ModelConfig:
       # lambda: 0.0 = prefer accuracy, 1.0 = prefer cost
       # complexity: 0.0 = simple, 1.0 = complex

       # Adjust threshold based on lambda
       premium_threshold = 0.8 - (lambda_param * 0.3)  # 0.8 to 0.5
       flash_threshold = 0.2 + (lambda_param * 0.3)  # 0.2 to 0.5

       if complexity >= premium_threshold:
           return registry.get_by_tier("premium")
       elif complexity <= flash_threshold:
           return registry.get_by_tier("flash")
       else:
           return registry.get_by_tier("standard")
   ```

8. **Token Usage Extraction in SubAgent:**
   ```python
   async def _call_llm(self, prompt: str, tools: list[dict[str, Any]]) -> tuple[Any, CostRecord]:
       response = await self.client.chat.completions.create(...)

       # Extract usage
       usage = response.usage
       if usage:
           prompt_tokens = usage.prompt_tokens
           completion_tokens = usage.completion_tokens
           total_tokens = usage.total_tokens
       else:
           # Fallback estimation
           prompt_tokens = len(prompt) // 4
           completion_tokens = 100  # Rough estimate
           total_tokens = prompt_tokens + completion_tokens

       # Calculate cost
       cost = calculate_cost(prompt_tokens, completion_tokens, self.tuple.model)

       record = CostRecord(
           model_name=self.tuple.model.name,
           prompt_tokens=prompt_tokens,
           completion_tokens=completion_tokens,
           total_tokens=total_tokens,
           estimated_cost=cost,
       )

       return response, record
   ```

9. **Orchestrator Integration:**
   ```python
   async def _delegate(self, action: DelegateAction) -> tuple[Observation, CostRecord]:
       # Estimate complexity
       complexity = estimate_complexity(
           action.instruction,
           action.tools,
           len(action.context),
       )

       # Select model
       model = select_model(complexity, self.lambda_param, self.model_registry)

       # Build tuple with selected model
       tuple_def = AgentTuple(
           instruction=action.instruction,
           context=self._build_context_for_subagent(action),
           tools=self._filter_tools(action.tools),
           model=model,  # Use selected model
       )

       # Execute
       observation, cost_record = await self.factory.create_and_execute(tuple_def)

       # Track cost
       self.cost_tracker.track(cost_record)

       return observation, cost_record
   ```

### Implementation Order

Priority order based on dependencies and complexity:

1. **Model registry and tiers** (models/registry.py)
   - No dependencies, foundational
   - Follow ToolRegistry pattern

2. **Cost tracking models** (models/cost.py)
   - Depends on ModelConfig
   - Pydantic models for cost data

3. **SubAgent modifications** (core/agents.py)
   - Extract token usage from LLM responses
   - Return CostRecord

4. **Model selection logic** (orchestrator/selection.py)
   - Independent logic for complexity estimation
   - Can test separately

5. **Orchestrator integration** (core/orchestrator.py, orchestrator/state.py)
   - Depends on all above
   - Main orchestration changes

6. **Configuration** (config.py)
   - Add cost rates and lambda configuration
   - Environment variable support

7. **Testing** (tests/test_model_registry.py, tests/test_cost_tracking.py, etc.)
   - Parallel with implementation
   - Comprehensive test coverage

### Testing Strategy

Follow existing testing patterns (items 001-003):

1. **Unit Tests:**
   - Test ModelRegistry registration and selection
   - Test complexity estimation logic
   - Test CostRecord creation and cost calculation
   - Test model selection with different lambda values
   - Mock token usage data for cost tracking tests

2. **Integration Tests:**
   - Test Orchestrator with ModelRegistry
   - Test cost tracking across multiple delegations
   - Test model selection for tasks of varying complexity
   - Verify total cost calculation

3. **End-to-End Tests:**
   - Test full workflow with cost-aware routing
   - Compare costs with vs without model selection
   - Test error handling (missing usage data, unavailable models)
   - (Optional) Test with real LLM and verify actual costs

4. **Test Fixtures:**
   - Mock token usage: `create_mock_usage(prompt_tokens=100, completion_tokens=50)`
   - Mock model registry with predefined tiers
   - Sample CostRecord objects
   - Test tasks with known complexity

5. **Mocking Patterns:**
   ```python
   # Mock OpenAI response with usage
   mock_response = MagicMock()
   mock_response.choices = [MagicMock()]
   mock_response.choices[0].message.content = "Response"
   mock_response.choices[0].message.tool_calls = None
   mock_response.usage = MagicMock(
       prompt_tokens=100,
       completion_tokens=50,
       total_tokens=150,
   )
   ```

## Open Questions

**Clarifications needed:**

1. **Cost rate accuracy** - What are the actual cost rates for Z.ai models (glm-4-flash, glm-4.7, etc.)?
   - If not publicly available, should we:
     - Use estimated rates?
     - Make rates configurable via environment variables?
     - Document them as estimates?

2. **Model tier availability** - Are there actually 3+ distinct models available on Z.ai API?
   - If only 2 models available, should we:
     - Define tiers within the same model (different temperature/max_tokens)?
     - Wait for Z.ai to release more models?
     - Document limitation?

3. **Lambda parameter default** - What should be the default lambda value?
   - Options: 0.0 (accuracy-first), 0.5 (balanced), 1.0 (cost-first)
   - Recommendation: 0.5 (balanced) to demonstrate trade-off

4. **Complexity estimation approach** - Should complexity estimation be:
   - Simple heuristics (instruction length, tools, context)?
   - LLM-based (call orchestrator's model to estimate complexity)?
   - Hybrid (heuristics first, LLM as fallback)?

5. **Observation vs Delegation for cost** - Where should cost information be stored?
   - Option A: Add `token_usage` field to Observation
   - Option B: Add `cost_record` field to Delegation
   - Option C: Separate cost tracking via CostTracker only

6. **Backward compatibility** - Should cost tracking be optional to avoid breaking changes?
   - Option A: Make cost tracking always on
   - Option B: Add `enable_cost_tracking` flag to Orchestrator
   - Recommendation: Always on, but gracefully handle missing data

7. **Model selection granularity** - Should model selection happen:
   - Per delegation (subtask level)?
   - Per tool invocation?
   - Per orchestrator decision step?
   - Recommendation: Per delegation (item 004 scope)

8. **Cost aggregation** - Should costs be aggregated:
   - Per orchestrator session (OrchestratorState)?
   - Per goal?
   - Globally across all orchestrator instances?
   - Recommendation: Per orchestrator session

9. **Token usage fallback** - If `response.usage` is not available, should we:
   - Estimate based on input length?
   - Skip cost tracking for that delegation?
   - Raise a warning and use zero cost?

10. **Model selection override** - Should the LLM (via DelegateAction) be able to request a specific model?
    - Option A: Add optional `model_tier` field to DelegateAction
    - Option B: Orchestrator always decides model selection
    - Recommendation: Start with orchestrator decision, consider LLM request in future

11. **Cost tracking precision** - Should costs be tracked as:
    - Float (USD with decimals)?
    - Cents (integer)?
    - Recommendation: Float for flexibility, document precision (e.g., 6 decimal places)

12. **Testing with real API** - Should item 004 include integration tests with real Z.ai API?
    - Real API would provide actual token usage and costs
    - But requires API keys and incurs cost
    - Recommendation: Optional, with fallback to mocks

13. **Documentation level** - How much documentation is needed for:
    - Cost rate configuration?
    - Lambda parameter tuning?
    - Model tier capabilities?
    - Recommendation: Comprehensive documentation with examples

14. **Performance monitoring** - Should item 004 include:
    - Latency tracking per model tier?
    - Cost/accuracy trade-off metrics?
    - Recommendation: Focus on cost tracking, defer performance metrics to item 005

15. **Error handling** - How should system handle:
    - Cost tracking errors (invalid cost rates)?
    - Model unavailability (requested tier not available)?
    - Recommendation: Fallback to standard model, log warnings, continue execution
