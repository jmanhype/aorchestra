# Research: Core 4-tuple agent abstraction

**Date**: 2025-01-18
**Item**: 001-core-4tuple-agent-abstraction

## Research Question

Implement the AgentTuple dataclass with (Instruction, Context, Tools, Model) fields. Create an AgentFactory that instantiates executable sub-agents from tuples. Each sub-agent runs in isolation with only its assigned context and tools. Include a base SubAgent class with execute() method that takes the tuple, builds a prompt from Instruction+Context, calls the Model with available Tools, and returns structured observations (result_summary, artifacts, error_logs).

**Motivation:** Foundation for the entire AOrchestra system - all other components depend on this abstraction.

**Success criteria:**
- AgentTuple dataclass with all 4 fields
- AgentFactory.create(tuple) returns executable SubAgent
- SubAgent.execute() calls LLM and returns structured observation
- Works with Z.ai/GLM models via OpenAI-compatible API

**Technical constraints:**
- Python 3.12+
- Use pydantic for data models
- OpenAI-compatible LLM client
- Async support

## Summary

This is a **greenfield implementation** - the AOrchestra project currently has no existing source code. The repository contains only documentation (README.md), configuration files (.wreckit/), and a Git repository structure with no Python packages or modules. Item 001 is the foundational component upon which all other items (002-005) explicitly depend.

The implementation requires creating the entire Python package structure from scratch, establishing the core 4-tuple agent abstraction that models any agent as Φ = (Instruction, Context, Tools, Model). This abstraction must support:
1. **Data modeling** with Pydantic for type safety and validation
2. **Async execution** via OpenAI-compatible API clients (for Z.ai/GLM models)
3. **Factory pattern** for dynamic sub-agent instantiation
4. **Isolation** ensuring each sub-agent only accesses its assigned context and tools
5. **Structured observations** returning result_summary, artifacts, and error_logs

The implementation should follow LangChain/LangGraph patterns since they're mentioned in the stack, but must be designed to work with any OpenAI-compatible LLM backend (Z.ai/GLM-4.7 default).

## Current State Analysis

### Existing Implementation

**Current State: No implementation exists**

The project is at its initial state:
- **README.md:1-24** - Defines the core concept: "Any agent is a dynamically instantiable 4-tuple: Φ = (Instruction, Context, Tools, Model)" and mentions the stack (Python 3.12+, LangChain/LangGraph, GLM-4.7 via Z.ai)
- **.wreckit/items/001-core-4tuple-agent-abstraction/item.json:1-1** - Contains the item definition with success criteria and technical constraints
- **No source code** - No Python packages, modules, or dependencies configured yet

### Current Patterns and Conventions

Since this is a greenfield project, there are no existing implementation patterns to follow. However, the README.md establishes:
- **Architectural pattern**: Orchestrator → Delegate(Φ) → Sub-Agent → observation
- **Core abstraction**: 4-tuple structure Φ = (Instruction, Context, Tools, Model)
- **LLM backend**: GLM-4.7 via Z.ai as default, with OpenAI-compatible API
- **Stack preference**: LangChain/LangGraph for agent orchestration

### Integration Points

**Downstream dependencies** (from item.json files):
- **Item 002** (Orchestrator): Explicitly depends on item 001 for AgentTuple and SubAgent
- **Item 003** (ToolRegistry): Depends on items 001 and 002 for consistent tool interface
- **Item 004** (ModelRouting): Depends on items 001 and 002 for ModelRegistry integration

All integration points are currently theoretical - no integration code exists yet.

## Key Files

### Project Documentation

- **README.md:1-24** - Project overview and architectural concept
  - Lines 5-7: Defines the 4-tuple abstraction Φ = (Instruction, Context, Tools, Model)
  - Lines 9-15: Shows the orchestration architecture flow
  - Lines 17-20: Lists the technology stack (Python 3.12+, LangChain/LangGraph, GLM-4.7)

### Item Definitions

- **.wreckit/items/001-core-4tuple-agent-abstraction/item.json:1-1** - Item 001 definition
  - Specifies success criteria: AgentTuple dataclass, AgentFactory, SubAgent.execute()
  - Technical constraints: Python 3.12+, Pydantic, OpenAI-compatible API, async support
  - Problem statement: "Need a foundational agent abstraction that models any agent as a 4-tuple"

- **.wreckit/items/002-orchestrator-delegate-finish/item.json:1-1** - Shows explicit dependency on item 001
  - Technical constraints line: "Depends on item 001 (AgentTuple, SubAgent)"
  - Success criteria reference "Delegate(Phi)" where Phi is the 4-tuple from item 001

- **.wreckit/items/003-dynamic-context-tool-selection/item.json:1-1** - Tool requirements
  - Mentions "at least 4 built-in tools: calculator, code_execute, web_search_mock, file_read"
  - Tools must have "consistent interface (name, description, execute)"

- **.wreckit/items/004-cost-aware-model-routing/item.json:1-1** - Model registry requirements
  - References "ModelRegistry with 3+ model tiers (flash, standard, premium)"
  - All models accessible via Z.ai API

### Configuration Files

- **.wreckit/config.json:1-1** - Workflow configuration (not relevant to implementation)
- **.gitignore:1-3** - Only ignores .wreckit/config.local.json

## Technical Considerations

### Dependencies

**External Dependencies Required:**

1. **pydantic** (version 2.x) - For data models and validation
   - Required by technical constraints
   - Use for AgentTuple, Observation, and all data structures

2. **OpenAI-compatible async client** - For LLM communication
   - Option A: `openai` >= 1.0 (official SDK, supports custom base URLs for Z.ai)
   - Option B: `langchain-openai` (if following LangChain stack preference)
   - Must support async operations (`async/await`)
   - Must work with Z.ai's GLM-4.7 endpoint

3. **asyncio** - For concurrent sub-agent execution
   - Standard library in Python 3.12+
   - Required for isolation and parallel execution

4. **langchain** and/or **langgraph** - Optional but mentioned in stack
   - May use LangChain's tool abstraction
   - May use LangGraph for state management (but likely for item 002)
   - Not strictly required for item 001's core functionality

**Internal Modules to Create:**

1. **Core data models** (new package/module needed)
   - `aorchestra/core/tuples.py` - AgentTuple dataclass
   - `aorchestra/core/agents.py` - SubAgent base class
   - `aorchestra/core/factory.py` - AgentFactory
   - `aorchestra/core/observations.py` - Observation result structures

2. **Tool abstraction** (foundation for item 003)
   - `aorchestra/tools/base.py` - Base tool interface
   - Must support: name, description, execute pattern (from item 003)

3. **Model registry** (foundation for item 004)
   - `aorchestra/models/base.py` - Model configuration
   - Support for Z.ai/GLM models with OpenAI-compatible API

### Patterns to Follow

Since this is greenfield, we establish patterns:

1. **Pydantic for all data structures**
   - AgentTuple as a Pydantic dataclass or BaseModel
   - All observations and results as Pydantic models
   - Enables validation, serialization, and IDE support

2. **Async-first design**
   - All LLM calls use async/await
   - SubAgent.execute() is async
   - Factory supports concurrent agent creation

3. **Factory pattern for agent instantiation**
   - AgentFactory.create(tuple) returns configured SubAgent instances
   - Hides initialization complexity from orchestrator

4. **Isolation guarantees**
   - Each SubAgent receives only its assigned context and tools
   - No shared state between agents
   - Structured observations prevent leakage

5. **OpenAI compatibility**
   - Use standard OpenAI client with custom base URL
   - Support for tool/function calling (if GLM-4.7 supports it)
   - Fallback to prompt-based tool invocation if needed

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| **Z.ai API compatibility** | High | Z.ai claims OpenAI-compatible API, but must verify GLM-4.7 supports tool calling and async operations. Implement fallback to manual prompt-based tool execution if native tool calling unavailable. Test API endpoints early in implementation. |
| **Pydantic v2 compatibility** | Medium | Ensure LangChain/LangGraph work with Pydantic v2 (some older libraries assume v1). Pin dependency versions explicitly in requirements.txt/pyproject.toml. |
| **Async complexity** | Medium | Async SubAgent execution adds complexity (event loop management, error handling). Use clear async patterns, provide sync wrapper if needed, document async requirements. |
| **Tool interface ambiguity** | Medium | Item 003 defines tool interface but item 001 needs tools working now. Design extensible tool base class that can accommodate item 003's requirements (name, description, execute). Start simple, allow enhancement. |
| **Model routing coupling** | Low | Item 004 wants ModelRegistry, but item 001 needs model selection now. Design Model as a simple configuration type (name, parameters) that can be wrapped by ModelRegistry later. Avoid over-engineering. |
| **Observation structure rigidity** | Medium | Structured observations (result_summary, artifacts, error_logs) must be flexible enough for diverse use cases. Use Pydantic models with Optional fields and extensible metadata. |
| **No existing test infrastructure** | Medium | No tests, pytest config, or CI setup exists. Establish testing patterns alongside implementation (create tests/ directory, pytest.ini, example tests). |
| **LangChain/LangGraph learning curve** | Low | Stack mentions these but they're not strictly required. Can implement without them initially. Use them only if they clearly simplify the 4-tuple abstraction. |

## Recommended Approach

### High-Level Strategy

Since this is a foundational greenfield component with 4 downstream dependencies, implement incrementally with **test-driven development**:

**Phase 1: Core Data Models (Foundation)**
1. Create package structure: `aorchestra/` with `__init__.py`
2. Implement `AgentTuple` as Pydantic dataclass with 4 fields
3. Implement `Observation` result structure (result_summary, artifacts, error_logs)
4. Write unit tests for data validation and serialization
5. **Verification**: Tests pass, models validate correctly

**Phase 2: Tool and Model Abstractions**
1. Create base `Tool` protocol/class (name, description, execute method)
2. Create `Model` configuration class (model_name, parameters, api_base)
3. Implement mock tools for testing (echo_tool, error_tool)
4. Write tests for tool execution interface
5. **Verification**: Mock tools execute, models configure correctly

**Phase 3: SubAgent Base Class**
1. Implement `SubAgent` base class with async `execute()` method
2. Build prompt from Instruction + Context (template system)
3. Integrate OpenAI client for async LLM calls
4. Implement tool invocation (manual or native, based on API capabilities)
5. Return structured Observation from execute()
6. Write integration tests with mocked LLM responses
7. **Verification**: SubAgent.execute() returns proper observations

**Phase 4: AgentFactory**
1. Implement `AgentFactory.create(tuple)` method
2. Factory instantiates SubAgent with tuple configuration
3. Add validation (tuple has required fields, tools callable, model valid)
4. Test factory with various tuple configurations
5. **Verification**: Factory creates agents, rejects invalid tuples

**Phase 5: Z.ai Integration**
1. Configure OpenAI client for Z.ai endpoint (custom base_url)
2. Test real GLM-4.7 API calls (if credentials available)
3. Verify tool calling support or implement fallback
4. Document API configuration and usage
5. **Verification**: Real LLM calls work with Z.ai

### Architectural Decisions

1. **Package Structure:**
   ```
   aorchestra/
   ├── __init__.py
   ├── core/
   │   ├── __init__.py
   │   ├── tuples.py       # AgentTuple
   │   ├── agents.py       # SubAgent
   │   ├── factory.py      # AgentFactory
   │   └── observations.py # Observation, ObservationResult
   ├── tools/
   │   ├── __init__.py
   │   └── base.py         # Tool protocol
   └── models/
       ├── __init__.py
       └── config.py       # Model configuration
   ```

2. **Pydantic for everything:**
   - AgentTuple as `pydantic.dataclasses.dataclass`
   - Observation as `pydantic.BaseModel`
   - Enables JSON serialization for state persistence (item 002)

3. **Tool interface (anticipating item 003):**
   ```python
   class Tool(Protocol):
       name: str
       description: str
       async def execute(self, **kwargs) -> Any: ...
   ```

4. **Model configuration (anticipating item 004):**
   ```python
   class ModelConfig(BaseModel):
       name: str  # e.g., "glm-4.7", "glm-4-flash"
       api_base: str
       temperature: float = 0.7
       max_tokens: int = 2048
   ```

5. **Prompt construction:**
   - Simple template: f"{instruction}\n\nContext:\n{context}"
   - Can be enhanced later (item 003's context curation)
   - Keep flexible for template system evolution

### Implementation Order

Priority order based on dependencies and complexity:
1. **Data models** (AgentTuple, Observation) - No dependencies
2. **Tool/Model abstractions** - Foundation for execution
3. **SubAgent** - Core execution logic
4. **AgentFactory** - Simple wrapper around SubAgent
5. **Z.ai integration** - Can be mocked initially

### Testing Strategy

Since no test infrastructure exists:
1. Create `tests/` directory alongside `aorchestra/`
2. Create `pytest.ini` with async support (`asyncio_mode = auto`)
3. Mock LLM responses using `pytest.mock` or `unittest.mock`
4. Test data model validation extensively
5. Test SubAgent.execute() with mocked OpenAI client
6. Integration tests with real Z.ai API (optional, require credentials)

## Open Questions

**None** - All critical design decisions can be made during implementation with the flexible architecture outlined above.

**Clarifications (not blockers):**
- **Tool calling format**: Does GLM-4.7 support OpenAI's native tool/function calling? If not, implement manual prompt-based tool invocation. This is a runtime implementation detail, not a design blocker.
- **Prompt template system**: Keep simple for item 001. Item 003's context curation can introduce more sophisticated templating.
- **State persistence**: Item 002 needs state history. Item 1's Observation should be serializable (use Pydantic) but doesn't need persistence logic yet.

**Decisions Made:**
- Use Pydantic v2 (current standard)
- Use official `openai` SDK with custom base_url for Z.ai
- Make SubAgent.execute() async (required by constraints)
- Design tool base class to accommodate item 003's requirements
- Keep model configuration simple (ModelConfig) for item 004 to extend later
