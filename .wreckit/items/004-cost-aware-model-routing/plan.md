# Cost-aware model routing Implementation Plan

## Implementation Plan Title

Cost-aware model routing with ModelRegistry, CostTracker, and complexity-based selection

## Overview

Implement intelligent model selection where orchestrator dynamically chooses between cheap/fast models for simple subtasks and expensive/capable models for complex ones. The system tracks token usage and estimated monetary costs per delegation, enabling Pareto-efficient cost-performance trade-offs. Implementation includes a ModelRegistry with 3+ tiers (flash, standard, premium), a CostTracker for monitoring token usage and costs, complexity estimation heuristics, and a configurable lambda parameter controlling cost-performance trade-off.

## Current State

Items 001-003 are complete and production-ready. The orchestrator currently uses a single hardcoded ModelConfig for all delegations regardless of task complexity. The SubAgent._call_llm() method makes OpenAI API calls but does not extract token usage information from responses. ModelConfig is a simple dataclass with no tier information or cost tracking. No cost monitoring exists in the system.

**Key constraints discovered:**
- ToolRegistry pattern (from item 003) must be followed for ModelRegistry
- Pydantic models are used for all data structures
- Async-first design throughout the codebase
- Z.ai API is the primary backend (models: glm-4-flash, glm-4.7, etc.)
- No public pricing documentation for Z.ai models (cost rates must be estimated and configurable)

**Files that will be modified:**
- `aorchestra/core/agents.py:105-135` - Extract token usage from LLM responses
- `aorchestra/core/agents.py:155` - Process and return cost information
- `aorchestra/core/orchestrator.py:199-215` - Replace hardcoded model selection with ModelRegistry
- `aorchestra/core/orchestrator.py:36-40` - Add ModelRegistry and lambda to constructor
- `aorchestra/orchestrator/state.py:16-46` - Add cost tracking to Delegation
- `aorchestra/orchestrator/state.py:48-76` - Add total_cost to OrchestratorState
- `aorchestra/config.py:12-25` - Add cost_rates and lambda configuration

## Desired End State

The orchestrator intelligently selects models based on task complexity and the lambda parameter. Token usage and costs are tracked for every delegation. A ModelRegistry manages 3+ model tiers with configurable cost rates. Complexity heuristics estimate task difficulty from instruction, tools, and context. The system provides cost summaries and enables cost-aware decision making.

### Key Discoveries:

- **Pattern to follow**: ToolRegistry in `aorchestra/tools/registry.py:52-174` provides complete implementation of registry pattern with metadata, validation, and selection criteria
- **Constraint to work within**: ModelConfig is a Pydantic dataclass at `aorchestra/models/config.py:1-57`, cannot be changed to BaseModel without breaking changes
- **Token usage extraction point**: SubAgent._call_llm() at line 135 returns raw OpenAI response, usage data is in `response.usage` attribute
- **Hardcoded model selection**: Orchestrator._delegate() at line 211 uses `model=self.model`, needs dynamic selection
- **Missing cost tracking**: Observation at `aorchestra/core/observations.py:1-43` has result_summary, artifacts, error_logs but no cost data
- **State management**: OrchestratorState at `aorchestra/orchestrator/state.py:48-76` tracks history but not costs
- **Test patterns**: test_tool_registry.py shows comprehensive registry testing with mocks, similar approach needed for ModelRegistry

## What We're NOT Doing

1. **LLM-based complexity estimation** - Using simple heuristics instead (instruction length, tool complexity, context size)
2. **Real-time API cost tracking** - Using estimated costs based on token counts, not billing data
3. **Performance metrics** - Not tracking latency per model tier (deferred to item 005)
4. **Cost optimization algorithms** - Simple threshold-based model selection, not ML-based optimization
5. **Automatic cost rate discovery** - Cost rates are configured, not fetched from API
6. **Model availability checking** - Assuming models are available, not validating at runtime
7. **Per-tool model selection** - Model selection is per-delegation, not per-tool invocation
8. **Cost budget enforcement** - No hard cost limits or budget management
9. **Cost comparison dashboards** - No UI or reporting for cost analysis
10. **Model fine-tuning based on cost** - Not adjusting model parameters to reduce costs

## Implementation Approach

Follow the ToolRegistry pattern from item 003 as the reference architecture. Implement cost-aware routing in phases, each independently testable. Use Pydantic for all new data models. Maintain backward compatibility where possible (cost tracking is always on but handles missing data gracefully).

**Key design decisions:**

1. **ModelRegistry** follows ToolRegistry structure with register(), get(), select_model() methods
2. **CostTracker** stores CostRecord objects and provides aggregation methods
3. **CostRecord** is added to Delegation model, not Observation (keeps observation focused on task results)
4. **Complexity estimation** uses simple heuristics (instruction length, tools, context size)
5. **Model selection** uses lambda parameter with adjustable thresholds (lambda: 0.0=accuracy, 1.0=cost)
6. **Token usage extraction** happens in SubAgent._call_llm(), returns tuple of (response, CostRecord)
7. **Cost rates** are estimated and configurable via environment variables
8. **Model tiers**: flash (glm-4-flash), standard (glm-4.7), premium (glm-4-plus or glm-4.7 with higher tokens/temperature)

---

## Phases

### Phase 1: Create Cost Tracking Models

#### Overview

Create Pydantic models for cost tracking (CostRecord, ModelTier, ModelMetadata). These are foundational data structures for the entire feature.

#### Changes Required:

##### 1. Create models/cost.py

**File**: `aorchestra/models/cost.py`
**Changes**: New file containing cost tracking Pydantic models

The file will contain:
- CostRecord model with model_name, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, timestamp
- from_openai_usage() class method to create CostRecord from OpenAI responses
- ModelTier model with name, tier, description, cost_per_1k_input, cost_per_1k_output, capabilities
- ModelSelectionCriteria model with complexity, lambda_param, tier_preference

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_cost_models.py -v`
- [ ] Type checking passes: `mypy aorchestra/models/cost.py`
- [ ] Linting passes: `ruff check aorchestra/models/cost.py`

##### Manual Verification:

- [ ] CostRecord can be created with valid data
- [ ] CostRecord.from_openai_usage() correctly calculates costs
- [ ] ModelTier accepts valid tier values
- [ ] ModelSelectionCriteria validates complexity and lambda ranges
- [ ] All models serialize/deserialize to/from JSON correctly

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 2: Create CostTracker Class

#### Overview

Implement CostTracker class to aggregate cost records and provide summary statistics.

#### Changes Required:

##### 1. Add CostTracker to models/cost.py

**File**: `aorchestra/models/cost.py`
**Changes**: Add CostTracker class at end of file

The class will contain:
- __init__() to initialize empty records list
- track(record) to add cost records
- get_total_cost() to sum all costs
- get_total_tokens() to sum all tokens
- get_delegation_count() to return number of records
- get_summary() to return comprehensive breakdown
- reset() to clear all records
- get_records() to return copy of records

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_cost_tracker.py -v`
- [ ] Type checking passes: `mypy aorchestra/models/cost.py`
- [ ] Linting passes: `ruff check aorchestra/models/cost.py`

##### Manual Verification:

- [ ] CostTracker tracks multiple cost records
- [ ] get_total_cost() correctly sums costs
- [ ] get_total_tokens() correctly sums tokens
- [ ] get_summary() includes model breakdown
- [ ] reset() clears all records
- [ ] get_records() returns copy (not internal list)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 3: Create ModelRegistry Class

#### Overview

Implement ModelRegistry following the ToolRegistry pattern to manage model tiers and provide selection logic.

#### Changes Required:

##### 1. Create models/registry.py

**File**: `aorchestra/models/registry.py`
**Changes**: New file containing ModelRegistry class

The class will contain:
- __init__() to initialize empty config and tier dicts
- register(config, tier) to add models with validation
- unregister(name) to remove models
- get(name) to get model config by name
- get_tier(name) to get tier metadata by name
- get_by_tier(tier) to get first model at tier level
- get_all() to return all model configs
- list_models() to return all model names
- select_model(criteria) to select model based on complexity and lambda
- __len__() and __contains__() dunder methods

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_model_registry.py -v`
- [ ] Type checking passes: `mypy aorchestra/models/registry.py`
- [ ] Linting passes: `ruff check aorchestra/models/registry.py`

##### Manual Verification:

- [ ] ModelRegistry registers models with validation
- [ ] get_by_tier() returns correct model for each tier
- [ ] select_model() uses tier_preference when set
- [ ] select_model() uses lambda to adjust thresholds
- [ ] select_model() handles edge cases (no models, missing tiers)
- [ ] Unregister removes model and tier metadata

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 4: Create Built-in Models Helper

#### Overview

Implement get_builtin_models() helper function to register default model tiers (flash, standard, premium) with estimated cost rates.

#### Changes Required:

##### 1. Add helper to models/registry.py

**File**: `aorchestra/models/registry.py`
**Changes**: Add get_builtin_models() function at end of file

The function will:
- Return list of (ModelConfig, ModelTier) tuples
- Define flash tier: glm-4-flash with estimated costs (~$0.0001 input, $0.0002 output)
- Define standard tier: glm-4.7 with estimated costs (~$0.001 input, $0.002 output)
- Define premium tier: glm-4-plus with estimated costs (~$0.01 input, $0.02 output)
- Allow optional cost_rates parameter to override defaults

##### 2. Update models/__init__.py

**File**: `aorchestra/models/__init__.py`
**Changes**: Export new modules

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_builtin_models.py -v`
- [ ] Type checking passes: `mypy aorchestra/models/`
- [ ] Linting passes: `ruff check aorchestra/models/`

##### Manual Verification:

- [ ] get_builtin_models() returns 3 model configurations
- [ ] Each model has valid tier metadata
- [ ] Cost rates are all positive
- [ ] All models can be registered in ModelRegistry
- [ ] Exports work correctly from aorchestra.models

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 5: Create Complexity Estimation Module

#### Overview

Implement complexity estimation heuristics in orchestrator/selection.py module.

#### Changes Required:

##### 1. Create orchestrator/selection.py

**File**: `aorchestra/orchestrator/selection.py`
**Changes**: New file containing complexity estimation logic

The module will contain:
- COMPLEXITY_KEYWORDS dict mapping keywords to weights
- COMPLEX_TOOLS dict mapping tool names to complexity scores
- estimate_complexity(instruction, tools, context_length) function returning 0.0-1.0
- select_model_by_criteria(complexity, lambda_param, model_registry, tier_preference) function

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_complexity_estimation.py -v`
- [ ] Type checking passes: `mypy aorchestra/orchestrator/selection.py`
- [ ] Linting passes: `ruff check aorchestra/orchestrator/selection.py`

##### Manual Verification:

- [ ] estimate_complexity() returns scores in [0, 1]
- [ ] Complexity keywords increase score appropriately
- [ ] Complex tools increase score appropriately
- [ ] Longer instructions increase score appropriately
- [ ] Larger context increases score appropriately
- [ ] select_model_by_criteria() integrates with ModelRegistry

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 6: Modify SubAgent to Extract Token Usage

#### Overview

Update SubAgent._call_llm() to extract token usage from OpenAI API responses and return CostRecord.

#### Changes Required:

##### 1. Modify SubAgent._call_llm() in core/agents.py

**File**: `aorchestra/core/agents.py:105-135`
**Changes**: Return tuple of (response, cost_record) and extract usage

- Import CostRecord from aorchestra.models.cost
- Extract usage from response.usage after API call
- Create CostRecord with prompt_tokens, completion_tokens, total_tokens
- Use estimated cost (0.0 placeholder) since model tier info not available
- Handle case where usage is None (estimate from prompt length)
- Return tuple of (response, cost_record)

##### 2. Update _execute_impl() to handle cost record

**File**: `aorchestra/core/agents.py:60-90`
**Changes**: Store and return cost record

- Receive cost_record from _call_llm()
- Return tuple of (Observation, cost_record)

##### 3. Update execute() method

**File**: `aorchestra/core/agents.py:48-58`
**Changes**: Return tuple from execute()

- Return tuple of (Observation, cost_record)
- Handle exceptions and return zero cost record on error

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_agents.py -v`
- [ ] Type checking passes: `mypy aorchestra/core/agents.py`
- [ ] Linting passes: `ruff check aorchestra/core/agents.py`

##### Manual Verification:

- [ ] SubAgent.execute() returns tuple of (Observation, CostRecord)
- [ ] CostRecord has valid token counts when usage available
- [ ] CostRecord uses estimates when usage not available
- [ ] Error cases return zero cost record
- [ ] Existing functionality preserved (no regressions)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 7: Update AgentFactory to Handle Cost Records

#### Overview

Modify AgentFactory.create_and_execute() to return cost record from SubAgent.

#### Changes Required:

##### 1. Update AgentFactory.create_and_execute()

**File**: `aorchestra/core/factory.py:18-36`
**Changes**: Return tuple with cost record

- Update return type to tuple[Observation, CostRecord]
- Return result from agent.execute() which now returns tuple

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_factory.py -v`
- [ ] Type checking passes: `mypy aorchestra/core/factory.py`
- [ ] Linting passes: `ruff check aorchestra/core/factory.py`

##### Manual Verification:

- [ ] AgentFactory.create_and_execute() returns tuple
- [ ] Cost record is passed through correctly
- [ ] No regressions in factory functionality

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 8: Update Delegation Model to Include Cost

#### Overview

Add cost_record field to Delegation model in orchestrator/state.py.

#### Changes Required:

##### 1. Update Delegation model

**File**: `aorchestra/orchestrator/state.py:16-46`
**Changes**: Add cost_record field

- Import CostRecord from aorchestra.models.cost
- Add cost_record field to Delegation model

##### 2. Update OrchestratorState with cost tracking

**File**: `aorchestra/orchestrator/state.py:48-76`
**Changes**: Add total_cost and get_cost_summary() methods

- Add total_cost_usd field to OrchestratorState
- Update add_delegation() to increment total_cost_usd
- Add get_cost_summary() method returning breakdown

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator_state.py -v`
- [ ] Type checking passes: `mypy aorchestra/orchestrator/state.py`
- [ ] Linting passes: `ruff check aorchestra/orchestrator/state.py`

##### Manual Verification:

- [ ] Delegation includes cost_record field
- [ ] OrchestratorState tracks total_cost_usd
- [ ] add_delegation() updates total cost
- [ ] get_cost_summary() returns correct breakdown
- [ ] Existing functionality preserved

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 9: Integrate ModelRegistry into Orchestrator

#### Overview

Modify Orchestrator to use ModelRegistry for intelligent model selection based on task complexity.

#### Changes Required:

##### 1. Update Orchestrator.__init__()

**File**: `aorchestra/core/orchestrator.py:36-53`
**Changes**: Add ModelRegistry, lambda parameter, CostTracker

- Import ModelRegistry, get_builtin_models, CostTracker, selection
- Add model_registry, lambda_param parameters to __init__()
- Initialize model_registry with built-in models if not provided
- Initialize CostTracker instance
- Update docstring to mention cost-aware routing

##### 2. Update Orchestrator._delegate()

**File**: `aorchestra/core/orchestrator.py:199-252`
**Changes**: Use ModelRegistry for model selection, track costs

- Import CostRecord, ModelSelectionCriteria
- Estimate complexity using selection.estimate_complexity()
- Select model using model_registry.select_model()
- Use selected model instead of self.model in AgentTuple
- Recalculate cost with actual model tier rates
- Track cost using cost_tracker.track()
- Return tuple of (Observation, CostRecord)

##### 3. Update _integrate_observation()

**File**: `aorchestra/core/orchestrator.py:254-277`
**Changes**: Pass cost_record to Delegation

- Add cost_record parameter
- Reconstruct tuple using same model selection logic
- Pass cost_record to Delegation constructor

##### 4. Update run() method

**File**: `aorchestra/core/orchestrator.py:78-96`
**Changes**: Handle cost_record from _delegate()

- Receive cost_record from _delegate()
- Log total cost on finish and max_steps reached
- Pass cost_record to _integrate_observation()

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator.py tests/test_orchestrator_integration.py -v`
- [ ] Type checking passes: `mypy aorchestra/core/orchestrator.py`
- [ ] Linting passes: `ruff check aorchestra/core/orchestrator.py`

##### Manual Verification:

- [ ] Orchestrator initializes with ModelRegistry and lambda_param
- [ ] _delegate() uses model selection based on complexity
- [ ] Cost records are tracked correctly
- [ ] OrchestratorState.total_cost_usd is updated
- [ ] Cost is calculated with actual model tier rates
- [ ] Different lambda values affect model selection
- [ ] Existing functionality preserved

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 10: Add Configuration Support

#### Overview

Add cost_rates and lambda configuration to Config class and .env.example.

#### Changes Required:

##### 1. Update config.py

**File**: `aorchestra/config.py:12-25`
**Changes**: Add cost_rates and lambda configuration

- Add cost_rates and lambda_param fields to Config dataclass
- Parse COST_RATES JSON from environment in from_env()
- Handle JSON decode errors with default rates
- Parse and clamp LAMBDA parameter to [0, 1] range

##### 2. Update .env.example

**File**: `.env.example`
**Changes**: Add cost and lambda configuration

- Add LAMBDA parameter with documentation
- Add COST_RATES JSON with model cost rates
- Document cost rate format and update instructions

##### 3. Update get_builtin_models() to use config

**File**: `aorchestra/models/registry.py`
**Changes**: Optionally load rates from config

- Add cost_rates parameter to get_builtin_models()
- Use provided rates or defaults

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_config.py -v`
- [ ] Type checking passes: `mypy aorchestra/config.py`
- [ ] Linting passes: `ruff check aorchestra/config.py`

##### Manual Verification:

- [ ] Config loads lambda from environment
- [ ] Config loads COST_RATES from environment
- [ ] Config handles invalid JSON gracefully
- [ ] get_builtin_models() accepts custom rates
- [ ] .env.example is clear and documented

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 11: Export Components

#### Overview

Export all new components from package-level __init__.py files.

#### Changes Required:

##### 1. Update aorchestra/__init__.py

**File**: `aorchestra/__init__.py`
**Changes**: Export new components

- Import from aorchestra.models.cost: CostRecord, CostTracker, ModelTier, ModelSelectionCriteria
- Import from aorchestra.models.registry: ModelRegistry, get_builtin_models
- Import from aorchestra.orchestrator.selection: estimate_complexity, select_model_by_criteria
- Add to __all__ list

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_exports.py -v`
- [ ] Type checking passes: `mypy aorchestra/__init__.py`
- [ ] Linting passes: `ruff check aorchestra/__init__.py`

##### Manual Verification:

- [ ] All components can be imported from aorchestra
- [ ] No circular import errors
- [ ] Package public API is clean

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 12: Write Comprehensive Unit Tests

#### Overview

Write unit tests for all new components following existing test patterns.

#### Changes Required:

##### 1. Create tests/test_cost_models.py

**File**: `tests/test_cost_models.py`
**Changes**: New test file for CostRecord, ModelTier, ModelSelectionCriteria

##### 2. Create tests/test_cost_tracker.py

**File**: `tests/test_cost_tracker.py`
**Changes`: New test file for CostTracker

##### 3. Create tests/test_model_registry.py

**File**: `tests/test_model_registry.py`
**Changes**: New test file for ModelRegistry

##### 4. Create tests/test_complexity_estimation.py

**File**: `tests/test_complexity_estimation.py`
**Changes`: New test file for complexity estimation

##### 5. Update existing tests for backward compatibility

**Files**: `tests/test_agents.py`, `tests/test_factory.py`, `tests/test_orchestrator.py`
**Changes**: Update tests to handle tuple returns (Observation, CostRecord)

#### Success Criteria:

##### Automated Verification:

- [ ] All new tests pass: `pytest tests/test_cost*.py tests/test_model_registry.py tests/test_complexity_estimation.py -v`
- [ ] All existing tests pass: `pytest tests/ -v`
- [ ] Test coverage > 90% for new modules
- [ ] Type checking passes: `mypy aorchestra/`
- [ ] Linting passes: `ruff check aorchestra/`

##### Manual Verification:

- [ ] CostRecord tests cover creation, validation, serialization
- [ ] CostTracker tests cover tracking, aggregation, summary
- [ ] ModelRegistry tests cover registration, selection, tier-based filtering
- [ ] Complexity estimation tests cover all factors (length, keywords, tools, context)
- [ ] All edge cases are tested
- [ ] Mocking patterns are consistent

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 13: Write Integration Tests

#### Overview

Write integration tests for end-to-end cost-aware routing scenarios.

#### Changes Required:

##### 1. Create tests/test_cost_aware_routing.py

**File**: `tests/test_cost_aware_routing.py`
**Changes**: New integration test file

The test file will include:
- test_simple_task_uses_flash_model: Verify simple tasks use flash model with high lambda
- test_complex_task_uses_premium_model: Verify complex tasks use premium model with low lambda
- test_cost_tracking_across_delegations: Verify cost tracking works across multiple delegations
- test_lambda_affects_model_selection: Verify lambda parameter affects selection
- test_complexity_estimation: Verify complexity scoring works correctly

#### Success Criteria:

##### Automated Verification:

- [ ] All integration tests pass: `pytest tests/test_cost_aware_routing.py -v`
- [ ] Test coverage for integration scenarios is adequate
- [ ] Tests run with mocked LLM responses (no real API calls)

##### Manual Verification:

- [ ] Simple tasks use appropriate models
- [ ] Complex tasks use appropriate models
- [ ] Lambda parameter affects model selection
- [ ] Cost tracking works across multiple delegations
- [ ] Complexity estimation produces sensible scores

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 14: Documentation and Examples

#### Overview

Create documentation and example demonstrating cost-aware routing.

#### Changes Required:

##### 1. Create examples/cost_aware_routing.py

**File**: `examples/cost_aware_routing.py`
**Changes**: New example file

The example will demonstrate:
- Creating Orchestrator with different lambda values
- Complexity estimation for simple vs complex tasks
- Model selection behavior
- Cost tracking and summaries

#### Success Criteria:

##### Automated Verification:

- [ ] Example runs without errors
- [ ] Example demonstrates cost-aware routing behavior

##### Manual Verification:

- [ ] Example shows different lambda values affecting model selection
- [ ] Example shows complexity estimation
- [ ] Example demonstrates cost tracking output
- [ ] Code is well-documented and clear

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 15: Final Verification

#### Overview

Run full test suite, check type checking, linting, and verify all acceptance criteria from item.json.

#### Changes Required:

##### 1. Run complete test suite

```bash
pytest tests/ -v --cov=aorchestra --cov-report=html
```

##### 2. Run type checking

```bash
mypy aorchestra/
```

##### 3. Run linting

```bash
ruff check aorchestra/
ruff format --check aorchestra/
```

##### 4. Verify acceptance criteria

From item.json:
- [ ] ModelRegistry with 3+ model tiers (flash, standard, premium)
- [ ] CostTracker monitoring token usage and estimated cost per delegation
- [ ] Lambda parameter controlling cost-performance trade-off
- [ ] Orchestrator uses complexity heuristics for model selection

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass (100% success rate)
- [ ] Test coverage > 90% for all new modules
- [ ] Type checking passes with no errors
- [ ] Linting passes with no warnings
- [ ] No regressions in existing functionality

##### Manual Verification:

- [ ] All acceptance criteria from item.json are met
- [ ] Cost-aware routing works as documented
- [ ] Documentation is complete and accurate
- [ ] Example code runs successfully
- [ ] Code follows existing patterns and conventions

**Note**: After completing all verification, implementation is ready for review and merging.

---

## Testing Strategy

### Unit Tests:

- **CostRecord, ModelTier, ModelSelectionCriteria**: Test creation, validation, serialization, JSON conversion, field validation (ge, le constraints)
- **CostTracker**: Test track(), get_total_cost(), get_total_tokens(), get_summary(), reset(), get_records(), aggregation across multiple records
- **ModelRegistry**: Test register() (valid, duplicate, name mismatch), unregister(), get(), get_tier(), get_by_tier(), get_all(), list_models(), select_model() with various criteria, __len__(), __contains__()
- **Complexity estimation**: Test estimate_complexity() with various instructions, tools, and context lengths; verify scores in [0, 1] range
- **SubAgent modifications**: Test that _call_llm() returns tuple, token extraction works, cost records are created
- **State model updates**: Test Delegation with cost_record, OrchestratorState.total_cost_usd updates, get_cost_summary()

### Integration Tests:

- **End-to-end orchestrator flow**: Test that orchestrator uses ModelRegistry for model selection based on task complexity
- **Lambda parameter effects**: Test different lambda values (0.0, 0.5, 1.0) verify they affect model selection
- **Cost tracking across delegations**: Test that costs are tracked and aggregated correctly across multiple delegations
- **Model selection for different tasks**: Test simple tasks use flash, medium tasks use standard, complex tasks use premium
- **Error handling**: Test that missing token usage data is handled gracefully
- **Configuration loading**: Test that COST_RATES and LAMBDA from environment are loaded correctly

### Manual Testing Steps:

1. Create simple orchestrator goal (e.g., "Add 2 + 2") with lambda=0.9
2. Verify that flash model is selected for the delegation
3. Verify cost tracking logs token usage and estimated cost
4. Create complex orchestrator goal (e.g., "Analyze and optimize this code for performance") with lambda=0.1
5. Verify that premium model is selected for the delegation
6. Verify that total cost is tracked across all delegations
7. Run orchestrator with lambda=0.5 (balanced)
8. Verify that model selection is appropriate for task complexity
9. Check that OrchestratorState.get_cost_summary() returns correct breakdown
10. Verify that invalid COST_RATES JSON in environment uses defaults

## Migration Notes

No migration needed for existing data. This is a new feature that adds cost tracking without breaking existing functionality.

**Backward compatibility considerations:**
- SubAgent.execute() signature changes from `Observation` to `tuple[Observation, CostRecord]`
- AgentFactory.create_and_execute() signature changes similarly
- Orchestrator._integrate_observation() gains cost_record parameter
- All tests that call these methods must be updated to handle tuple returns

**Breaking changes:**
- SubAgent.execute() and AgentFactory.create_and_execute() return tuples instead of single Observation
- Tests must be updated to unpack tuples

## References

- Research: `C:\Users\strau\clawd\aorchestra\.wreckit\items\004-cost-aware-model-routing/research.md`
- ToolRegistry pattern: `aorchestra/tools/registry.py:52-174`
- ModelConfig: `aorchestra/models/config.py:1-57`
- SubAgent: `aorchestra/core/agents.py:14-45`
- Orchestrator: `aorchestra/core/orchestrator.py:36-215`
- State models: `aorchestra/orchestrator/state.py:1-76`
- ToolRegistry PRD: `C:\Users\strau\clawd\aorchestra\.wreckit\items\003-dynamic-context-tool-selection/prd.json`
