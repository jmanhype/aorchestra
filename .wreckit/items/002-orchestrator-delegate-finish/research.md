# Research: Orchestrator with Delegate and Finish

**Date**: 2025-02-04
**Item**: 002-orchestrator-delegate-finish

## Research Question

Build the central Orchestrator class that never executes environment actions directly. It has exactly two system actions: Delegate(Phi) which spawns a sub-agent from a 4-tuple and collects its observation, and Finish(y) which terminates with a final answer. The orchestrator maintains a state history of all delegations and observations. It uses an LLM to decide at each step whether to Delegate (and with what tuple) or Finish.

## Summary

Item 002 implements the **Orchestrator**, the central decision-making component of AOrchestra. The orchestrator is responsible for decomposing complex tasks into subtasks, delegating to dynamically-created sub-agents, and synthesizing their observations into a final answer. Unlike sub-agents which execute tasks, the orchestrator only performs two system actions: **Delegate(Φ)** to spawn sub-agents, and **Finish(y)** to terminate with an answer.

The foundation (item 001) is **already implemented** with complete AgentTuple, SubAgent, Observation, and AgentFactory classes. The implementation includes Pydantic models for type safety, async execution support, OpenAI-compatible LLM integration, and comprehensive test coverage. Item 002 can directly depend on this stable foundation.

Key implementation requirements:
1. **Orchestrator class** with state machine managing delegation history
2. **LLM-based decision loop** that chooses between Delegate and Finish actions
3. **Delegate(Φ) action** that uses AgentFactory to create sub-agents and collect observations
4. **Finish(y) action** that terminates with a final answer
5. **State transition function** that integrates observations into history
6. **max_steps constraint** to prevent infinite loops
7. **Structured LLM output** for action selection (use OpenAI function calling or response parsing)

The orchestrator must maintain a **state history** of all delegations and observations, using this context to inform subsequent decisions. This history enables multi-step reasoning and context accumulation.

## Current State Analysis

### Existing Implementation

**Item 001 is complete and production-ready** - all core components are implemented and tested:

- **aorchestra/core/tuples.py:1-62** - `AgentTuple` dataclass with Instruction, Context, Tools, Model fields
  - Lines 13-31: Pydantic dataclass with validation
  - Lines 34-38: Field validator ensuring non-empty instruction
  - Lines 40-48: `build_prompt()` method combining instruction and context

- **aorchestra/core/agents.py:1-226** - `SubAgent` class with async execution
  - Lines 18-34: SubAgent initialization with AgentTuple and optional OpenAI client
  - Lines 36-56: Async `execute()` method with error handling
  - Lines 58-82: Internal `_execute_impl()` building prompts and calling LLM
  - Lines 84-103: `_prepare_tools()` converting tools to OpenAI function format
  - Lines 105-129: `_call_llm()` making async OpenAI API calls
  - Lines 131-168: Response processing and tool invocation logic
  - Lines 170-218: Tool call handling with error capture

- **aorchestra/core/observations.py:1-43** - `Observation` result structure
  - Lines 13-33: Pydantic BaseModel with result_summary, artifacts, error_logs
  - Lines 35-43: Helper methods for adding errors and artifacts

- **aorchestra/core/factory.py:1-109** - `AgentFactory` for agent creation
  - Lines 18-36: `create()` method with validation
  - Lines 38-73: `_validate_tuple()` checking instruction, tools, and model
  - Lines 75-87: `create_and_execute()` convenience method

- **aorchestra/tools/base.py:1-45** - Tool protocol interface
  - Lines 11-31: `Tool` Protocol with name, description, async execute
  - Lines 34-45: `validate_tool()` function for runtime validation

- **aorchestra/models/config.py:1-57** - Model configuration
  - Lines 12-36: `ModelConfig` dataclass with LLM parameters
  - Lines 47-51: `to_openai_kwargs()` for client initialization

### Current Patterns and Conventions

**Established patterns from item 001:**

1. **Pydantic for all data models** - AgentTuple, Observation, ModelConfig all use Pydantic
   - Provides validation, serialization, IDE support
   - Required for JSON serialization of state history

2. **Async-first design** - All execution is async
   - SubAgent.execute() is async (agents.py:36)
   - AgentFactory.create_and_execute() is async (factory.py:75)
   - Tool.execute() is async (tools/base.py:23)

3. **Protocol-based interfaces** - Tool uses Protocol for duck typing
   - Flexible tool registration (tools/base.py:11)
   - Runtime validation with `validate_tool()` (tools/base.py:34)

4. **Factory pattern** - AgentFactory creates SubAgents
   - Validates configuration before instantiation (factory.py:38)
   - Single creation method (factory.py:18)

5. **OpenAI compatibility** - All LLM calls use OpenAI client
   - Custom base_url for Z.ai (models/config.py:50)
   - Function calling support (agents.py:84-103)
   - Async client usage (agents.py:105-129)

6. **Error handling** - Errors captured in Observation.error_logs
   - SubAgent catches exceptions (agents.py:42-50)
   - Tool errors logged, not raised (agents.py:201-206)

7. **Testing patterns** - Comprehensive pytest tests
   - Async tests with pytest.mark.asyncio (tests/test_agents.py:35)
   - Mock OpenAI client for unit tests (tests/test_agents.py:37)
   - Validation error testing (tests/test_factory.py:52-68)

### Integration Points

**Item 002 depends on:**

1. **AgentTuple** (tuples.py) - Orchestrator creates 4-tuples for delegation
   - Must construct valid tuples with instruction, context, tools, model
   - Uses tuple.build_prompt() for sub-agent prompts

2. **AgentFactory** (factory.py) - Orchestrator spawns sub-agents
   - Calls factory.create(tuple) to get SubAgent
   - Uses factory.create_and_execute() for delegation

3. **Observation** (observations.py) - Orchestrator collects results
   - Receives observations from sub-agents
   - Accumulates in state history

4. **ModelConfig** (models/config.py) - Orchestrator configures models
   - Creates ModelConfig for sub-agent tuples
   - May select different models per subtask (item 004)

5. **Tool protocol** (tools/base.py) - Orchestrator selects tools
   - Filters tools for subtask (item 003)
   - Validates tools before delegation

**Downstream dependencies:**

- **Item 003** (ToolRegistry, context curation) - Enhances orchestrator's tool/context selection
- **Item 004** (ModelRegistry, cost tracking) - Adds model selection to orchestrator
- **Item 005** (evaluation) - Uses orchestrator in benchmark tasks

## Key Files

### Core Dependencies (Item 001)

- **aorchestra/core/tuples.py:1-62** - AgentTuple dataclass
  - Orchestrator creates these for delegation
  - Uses build_prompt() method for constructing sub-agent prompts
  - Validation ensures non-empty instruction

- **aorchestra/core/agents.py:1-226** - SubAgent execution engine
  - Orchestrator doesn't call this directly (uses factory)
  - Important for understanding execute() signature and Observation structure
  - Error handling pattern (lines 42-50) worth emulating

- **aorchestra/core/observations.py:1-43** - Observation result model
  - Orchestrator accumulates these in state history
  - Fields: result_summary, artifacts, error_logs
  - Pydantic model for serialization

- **aorchestra/core/factory.py:1-109** - AgentFactory
  - Primary interface for orchestrator's Delegate action
  - factory.create(tuple) returns SubAgent (lines 18-36)
  - factory.create_and_execute(tuple) returns Observation (lines 75-87)
  - Validation logic ensures safe delegation

- **aorchestra/tools/base.py:1-45** - Tool interface
  - Orchestrator must understand Tool protocol for tool selection
  - validate_tool() for runtime checks (line 34)

- **aorchestra/models/config.py:1-57** - Model configuration
  - Orchestrator creates ModelConfig for sub-agent tuples
  - to_openai_kwargs() for LLM client setup (line 47)

### Test Files (Patterns to Follow)

- **tests/test_factory.py:1-134** - Factory usage patterns
  - Shows how to create valid AgentTuples (lines 26-31)
  - Mock-based testing approach (lines 95-116)

- **tests/test_agents.py:1-186** - SubAgent execution testing
  - Async test patterns with pytest (lines 35-48)
  - Mock OpenAI client for unit tests (lines 37-44)
  - Error handling validation (lines 89-101)

- **examples/basic_agent.py:1-73** - Usage example
  - AgentTuple creation pattern (lines 20-26)
  - Factory usage (line 35)

- **examples/with_tools.py:1-56** - Tool usage example
  - Multi-tool tuple creation (lines 19-24)

### Configuration

- **pyproject.toml:1-37** - Project configuration
  - Dependencies: pydantic>=2.0, openai>=1.0 (line 14)
  - Async test mode: asyncio_mode = "auto" (line 33)
  - Test paths and Python files configured (lines 33-34)

- **requirements.txt:1-6** - Pinned dependencies
  - pydantic==2.7.4, openai==1.54.0
  - pytest with async support (pytest-asyncio==0.24.0)

### Item Definition

- **.wreckit/items/002-orchestrator-delegate-finish/item.json:1-1** - Item requirements
  - Success criteria listed (lines 15-19)
  - Explicit dependency on item 001 (line 26)
  - Requires max_steps constraint (line 27)
  - Requires structured LLM output (line 28)

- **README.md:1-24** - Overall architecture
  - Lines 9-15: Orchestrator architecture flow
  - Lines 17-20: Technology stack

## Technical Considerations

### Dependencies

**External Dependencies (already installed):**

1. **pydantic>=2.0** - For orchestrator state and action models
   - Use for OrchestratorState, DelegateAction, FinishAction
   - Enables JSON serialization for state history

2. **openai>=1.0** - For LLM-based decision making
   - Orchestrator uses OpenAI client for action selection
   - Function calling for structured output (Delegate vs Finish)
   - Async API for non-blocking decisions

3. **asyncio** - For async state machine execution
   - Orchestrator.run() should be async
   - Parallel delegation (future enhancement)

**Internal Dependencies (from item 001):**

1. **AgentTuple** (core/tuples.py)
   - Orchestrator creates tuples for sub-agents
   - Must provide instruction, context, tools, model

2. **AgentFactory** (core/factory.py)
   - Primary method for spawning sub-agents
   - factory.create_and_execute() for delegation

3. **Observation** (core/observations.py)
   - Results returned from sub-agents
   - Accumulated in state history

4. **ModelConfig** (models/config.py)
   - Model configuration for sub-agent tuples
   - May be extended by item 004's ModelRegistry

### Patterns to Follow

**From item 001:**

1. **Pydantic models for all state**
   ```python
   class OrchestratorState(BaseModel):
       step: int
       history: list[Delegation]
       current_goal: str
   ```

2. **Async methods for all execution**
   ```python
   async def run(self, goal: str) -> str:
       while self.state.step < self.max_steps:
           action = await self._decide_action()
           if isinstance(action, FinishAction):
               return action.answer
   ```

3. **Factory pattern for agent creation**
   ```python
   async def _delegate(self, tuple: AgentTuple) -> Observation:
       return await self.factory.create_and_execute(tuple)
   ```

4. **Error handling with structured capture**
   - Don't raise, capture in state/error_logs
   - Follow SubAgent pattern (agents.py:42-50)

5. **Protocol-based interfaces**
   - Action protocol (DelegateAction, FinishAction)
   - Flexible for extension

6. **Mock-based testing**
   - Mock LLM for decision logic testing
   - Mock factory for delegation testing

**New patterns for item 002:**

1. **State machine pattern**
   - Orchestrator maintains state across steps
   - State transition function integrates observations

2. **LLM-as-controller pattern**
   - Orchestrator uses LLM to choose actions
   - Structured output (function calling or parsing)

3. **History accumulation**
   - List of Delegation records (tuple, observation, step)
   - Used for context in future decisions

4. **Two-phase execution**
   - Decide action (LLM call)
   - Execute action (delegate or finish)

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| **Infinite delegation loops** | High | Implement max_steps constraint (required by item.json). Add detection of repeated delegation patterns. |
| **LLM decision quality** | High | Use structured output (function calling) not parsing. Provide clear system prompt. Test with diverse goals. |
| **State history bloat** | Medium | Implement context window management. Summarize old observations. Limit history length (configurable). |
| **Observation serialization** | Medium | Observation already uses Pydantic (item 001). Verify JSON serialization works for all artifact types. |
| **Async complexity** | Medium | Follow item 001's async patterns. Use clear async/await. Document execution model. |
| **AgentTuple validation** | Medium | AgentFactory validates tuples (factory.py:38). Rely on factory, don't duplicate validation. |
| **Tool selection for delegation** | Medium | For item 002, pass all tools or empty list. Item 003 will add intelligent selection. Keep interface flexible. |
| **Model selection for delegation** | Medium | For item 002, use default model from config. Item 004 will add ModelRegistry. Don't over-engineer. |
| **Testing LLM decisions** | Medium | Mock LLM responses for deterministic tests. Integration tests with real LLM for validation. |
| **Error recovery** | Low | Capture errors in Observation.error_logs. Don't fail on single sub-agent error. Continue delegation. |
| **Context construction** | Low | Use AgentTuple.build_prompt() (item 001). Don't reimplement. Pass relevant history as context. |

## Recommended Approach

### High-Level Strategy

Implement Orchestrator as an **async state machine** with LLM-based action selection:

**Phase 1: Core Data Models**
1. Create `OrchestratorState` Pydantic model (step, history, goal)
2. Create `DelegateAction` and `FinishAction` models (structured output)
3. Create `Delegation` record (tuple, observation, step)
4. Write unit tests for model validation and serialization
5. **Verification**: Models serialize to JSON correctly

**Phase 2: Orchestrator Class Structure**
1. Create `Orchestrator` class with state and factory
2. Implement `__init__()` with max_steps parameter
3. Implement `run(goal: str)` main loop
4. Implement `_decide_action()` method (stub initially)
5. Implement `_delegate()` and `_finish()` helper methods
6. Implement state transition in `_integrate_observation()`
7. Write unit tests for state transitions (with mocked actions)
8. **Verification**: State machine transitions correctly

**Phase 3: LLM-Based Decision Making**
1. Design system prompt for action selection
2. Implement `_decide_action()` with OpenAI function calling
   - Define functions: "delegate" and "finish"
   - Parse LLM response into DelegateAction or FinishAction
3. Add context construction from history
4. Write tests with mocked LLM responses
5. **Verification**: Orchestrator chooses correct actions based on prompts

**Phase 4: Delegation Integration**
1. Implement `_delegate(tuple)` using AgentFactory
2. Construct AgentTuple from DelegateAction
3. Call factory.create_and_execute(tuple)
4. Capture Observation in state history
5. Write integration tests with mocked factory
6. **Verification**: Delegations execute correctly, observations captured

**Phase 5: End-to-End Testing**
1. Create integration tests with real LLM (optional)
2. Test simple single-delegation scenarios
3. Test multi-delegation scenarios
4. Test max_steps termination
5. Test error handling (failed sub-agents)
6. **Verification**: Full orchestrator workflow functions correctly

### Architectural Decisions

1. **Package Structure:**
   ```
   aorchestra/
   ├── core/
   │   ├── tuples.py       # (existing) AgentTuple
   │   ├── agents.py       # (existing) SubAgent
   │   ├── factory.py      # (existing) AgentFactory
   │   ├── observations.py # (existing) Observation
   │   └── orchestrator.py # (NEW) Orchestrator class
   └── orchestrator/
       ├── __init__.py
       ├── state.py        # (NEW) OrchestratorState
       ├── actions.py      # (NEW) DelegateAction, FinishAction
       └── prompts.py      # (NEW) System prompts for LLM
   ```

2. **State Model:**
   ```python
   class Delegation(BaseModel):
       step: int
       tuple: AgentTuple
       observation: Observation
       timestamp: str

   class OrchestratorState(BaseModel):
       goal: str
       step: int
       history: list[Delegation]
       max_steps: int
   ```

3. **Action Models (for structured LLM output):**
   ```python
   class DelegateAction(BaseModel):
       instruction: str
       context: str
       tools: list[str]  # Tool names to include
       reasoning: str

   class FinishAction(BaseModel):
       answer: str
       reasoning: str
   ```

4. **LLM Decision Function:**
   - Use OpenAI function calling (not parsing)
   - Define two functions: "delegate_subagent" and "finish_task"
   - Force LLM to choose exactly one
   - Extract structured output from function call

5. **State Machine Loop:**
   ```python
   async def run(self, goal: str) -> str:
       self.state = OrchestratorState(goal=goal, step=0, history=[], max_steps=self.max_steps)
       
       while self.state.step < self.max_steps:
           action = await self._decide_action()
           
           if isinstance(action, FinishAction):
               return action.answer
           
           # Delegate
           tuple = self._build_tuple(action)
           observation = await self._delegate(tuple)
           self._integrate_observation(tuple, observation)
   ```

6. **Context Construction:**
   - Build context from state.history
   - Format previous delegations and observations
   - Pass as context to sub-agents (or use for LLM decision)
   - Keep concise to avoid context window issues

7. **Error Handling:**
   - Sub-agent errors captured in Observation.error_logs
   - Don't fail orchestrator on single delegation error
   - Continue delegation (or finish if critical)
   - Log all errors for debugging

### Implementation Order

Priority order based on dependencies and complexity:

1. **State and action models** (orchestrator/state.py, orchestrator/actions.py)
   - No dependencies, foundational
   - Pydantic models for type safety

2. **Orchestrator class structure** (core/orchestrator.py)
   - Depends on models
   - Main loop and state machine

3. **LLM decision making** (orchestrator/prompts.py + orchestrator.py)
   - Depends on orchestrator structure
   - Core intelligence

4. **Delegation integration** (orchestrator.py)
   - Depends on AgentFactory (item 001)
   - Connect to existing code

5. **Testing** (tests/test_orchestrator.py)
   - Parallel with implementation
   - Mock-based unit tests first
   - Integration tests last

### Testing Strategy

Follow item 001's testing patterns:

1. **Unit Tests (mocked LLM, mocked factory):**
   - Test state transitions
   - Test action selection logic
   - Test max_steps termination
   - Test error handling

2. **Integration Tests (real LLM, mocked factory):**
   - Test LLM decision quality
   - Test action parsing
   - Test context construction

3. **End-to-End Tests (real LLM, real factory):**
   - Test simple delegation scenarios
   - Test multi-step reasoning
   - Test error recovery
   - (Optional) Requires API keys

4. **Test Fixtures (conftest.py):**
   - Mock LLM client
   - Mock AgentFactory
   - Sample AgentTuples
   - Sample Observations

## Open Questions

**Clarifications needed:**

1. **Tool selection for delegation** - For item 002, should the orchestrator:
   - Always pass all available tools to sub-agents?
   - Let the LLM decide which tools to include?
   - This is simplified in item 002, enhanced in item 003 (ToolRegistry)
   - **Recommendation**: Include LLM decision for tool selection (list[str] tool names), keep it simple. Item 003 will add intelligent filtering.

2. **Model selection for delegation** - For item 002, should the orchestrator:
   - Always use a default model from config?
   - Support model selection per subtask?
   - Item 004 adds ModelRegistry with cost-aware routing
   - **Recommendation**: Use a default model (configurable in Orchestrator.__init__). Item 004 will add intelligent selection.

3. **Context window management** - How should the orchestrator handle long histories:
   - Pass full history to LLM for each decision?
   - Summarize old observations?
   - Limit history length?
   - **Recommendation**: For item 002, pass full history (assume small scale). Add configurable history_limit parameter. Document that item 003 may enhance this.

4. **Parallel delegation** - Should orchestrator support parallel sub-agents:
   - Delegate multiple agents simultaneously?
   - Or strictly sequential for item 002?
   - **Recommendation**: Sequential for item 002 (simpler). Parallel could be future enhancement (would need asyncio.gather and more complex state management).

5. **Finish action trigger** - When should orchestrator choose Finish:
   - LLM decides based on goal completion?
   - Explicit user termination?
   - Max_steps reached?
   - **Recommendation**: LLM decides (primary), max_steps (safety fallback), user termination (future enhancement).

**Decisions made during implementation:**

- Use OpenAI function calling for structured action selection (more reliable than parsing)
- Accumulate full Delegation records in history (tuple + observation)
- Use AgentTuple.build_prompt() for context construction (reuse item 001 logic)
- Implement max_steps as hard limit (configurable, default to 10-20)
- Capture all errors in state, don't raise
- Async throughout (follow item 001 pattern)
- Pydantic for all state and action models
