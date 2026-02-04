# Research: Dynamic context curation and tool selection

**Date**: 2025-02-04
**Item**: 003-dynamic-context-tool-selection

## Research Question

Implement the context routing system where the orchestrator curates task-relevant context for each sub-agent, filtering out distracting information. Build a ToolRegistry that manages available tools and allows the orchestrator to select subsets per subtask.

## Summary

Item 003 implements **dynamic context curation and intelligent tool selection** for the orchestrator. The foundation (items 001 and 002) is complete with full AgentTuple, SubAgent, Observation, AgentFactory, and Orchestrator implementations. The orchestrator currently has placeholder implementations for tool filtering (returns empty list) and basic context building (last 3 observations only).

Key implementation requirements:
1. **ToolRegistry** - A centralized registry managing all available tools with metadata (name, description, capabilities, tags)
2. **4 built-in tools** - calculator (exists), code_execute (new), web_search_mock (new), file_read (new)
3. **Intelligent tool selection** - Orchestrator analyzes subtask requirements and dynamically selects relevant tools per subtask
4. **Enhanced context curation** - Advanced filtering of task-relevant context beyond simple "last N" approach
5. **Replace placeholder** - Update Orchestrator._filter_tools() to use ToolRegistry instead of returning empty list

The tool registry must integrate seamlessly with existing Tool protocol (tools/base.py:12-41) and be accessible to the orchestrator for per-subtask tool selection. Context curation should analyze delegation history and subtask requirements to build focused, relevant context for each sub-agent.

## Current State Analysis

### Existing Implementation

**Items 001 and 002 are complete and production-ready** - all core infrastructure exists:

- **aorchestra/tools/base.py:1-45** - Tool protocol and validation
  - Lines 12-41: Tool Protocol with name, description, async execute signature
  - Lines 44-61: validate_tool() for runtime validation
  - Compatible with item 003's requirement for tools with "name, description, execute"

- **aorchestra/tools/mock.py:1-76** - Existing mock tools
  - Lines 7-26: EchoTool (simple echo for testing)
  - Lines 28-60: CalculatorTool (arithmetic operations)
  - Lines 62-76: ErrorTool (always raises error for testing)
  - CalculatorTool can serve as one of the required 4 built-in tools

- **aorchestra/core/agents.py:97-226** - SubAgent tool invocation
  - Lines 97-117: _prepare_tools() converts tools to OpenAI function format
  - Lines 146-164: _process_response() handles tool calls from LLM
  - Lines 169-213: _handle_tool_calls() executes tools and captures results
  - Lines 215-226: _find_tool() locates tools by name in tuple

- **aorchestra/core/orchestrator.py:199-312** - Orchestrator delegation logic
  - Lines 199-215: _delegate() method creates AgentTuple with tools
  - Lines 247-286: _build_context_for_subagent() builds context (basic implementation)
  - Lines 293-312: _filter_tools() - **PLACEHOLDER** (line 305: "TODO: Implement tool filtering in item 003")
  - Lines 109-162: _decide_action() uses LLM with function calling (includes "tools" parameter)

- **aorchestra/core/tuples.py:12-62** - AgentTuple structure
  - Lines 27-32: tools field (list[Any]) for tool assignment
  - Lines 40-48: build_prompt() method combining instruction and context

- **aorchestra/orchestrator/actions.py:12-31** - DelegateAction model
  - Lines 21-23: tools field (list[str]) for tool names requested by LLM

### Current Patterns and Conventions

**Established patterns from items 001-002:**

1. **Protocol-based interfaces** - Tool uses Protocol for duck typing (tools/base.py:12)
   - Allows any object with name, description, async execute
   - Runtime validation with validate_tool() (tools/base.py:44)

2. **Pydantic models for all data structures** - State, actions, tuples use Pydantic
   - AgentTuple, Observation, Delegation, OrchestratorState all use Pydantic
   - Enables validation and serialization

3. **Async-first design** - All tool execution is async (tools/base.py:30)
   - SubAgent.execute() is async (agents.py:36)
   - Orchestrator._delegate() is async (orchestrator.py:177)

4. **Factory pattern** - AgentFactory creates SubAgents (factory.py:18-36)
   - Validates tools via validate_tool() (factory.py:56-62)
   - ToolRegistry should follow similar pattern

5. **Error handling** - Errors captured in Observation.error_logs
   - Tool errors don't raise, get logged (agents.py:201-206)
   - Continue execution on failures

6. **Mock-based testing** - Comprehensive test coverage
   - tests/test_tools.py:1-128 tests tool protocol and mock tools
   - tests/test_agents.py:65-101 tests tool invocation

### Integration Points

**Item 003 must integrate with:**

1. **Orchestrator._filter_tools()** (orchestrator.py:293-312)
   - Currently returns empty list with TODO comment (line 305)
   - Must be replaced with ToolRegistry-based selection
   - Receives tool_names from DelegateAction (LLM decision)

2. **Orchestrator._build_context_for_subagent()** (orchestrator.py:263-286)
   - Currently includes action.context + last 3 observations
   - Should be enhanced with intelligent context filtering
   - Analyzes subtask requirements and delegation history

3. **Tool protocol** (tools/base.py:12-41)
   - All tools must implement Tool protocol
   - ToolRegistry must validate tools on registration
   - Built-in tools follow same interface

4. **AgentTuple.tools field** (tuples.py:27-32)
   - Receives filtered tools from orchestrator
   - Passed to SubAgent for execution
   - Must be list of tool objects (not names)

5. **AgentFactory** (factory.py:18-36)
   - Validates tools in _validate_tuple() (factory.py:56-62)
   - ToolRegistry tools should pass validation
   - Consider adding ToolRegistry to factory initialization

**Downstream dependencies:**

- **Item 004** (ModelRegistry) - May use similar registry pattern
- **Item 005** (evaluation) - Benefits from better context/tool selection

## Key Files

### Core Infrastructure (Items 001-002)

- **aorchestra/tools/base.py:1-45** - Tool protocol and validation
  - Lines 12-41: Tool Protocol definition (name, description, async execute)
  - Lines 44-61: validate_tool() function for runtime validation
  - All built-in tools must implement this protocol

- **aorchestra/tools/mock.py:1-76** - Existing tools
  - Lines 28-60: CalculatorTool (one of the 4 required built-in tools)
  - Lines 7-26: EchoTool (testing tool, can be retained)
  - Pattern to follow for new built-in tools

- **aorchestra/core/agents.py:97-226** - SubAgent tool handling
  - Lines 97-117: _prepare_tools() converts tools to OpenAI format
  - Lines 146-164: _process_response() checks for tool calls
  - Lines 169-213: _handle_tool_calls() executes tools and captures results
  - Lines 215-226: _find_tool() locates tools by name
  - Shows how tools are invoked and results integrated

- **aorchestra/core/orchestrator.py:199-312** - Orchestrator delegation
  - Lines 199-215: _delegate() creates AgentTuple with filtered tools
  - Lines 263-286: _build_context_for_subagent() (needs enhancement)
  - Lines 293-312: _filter_tools() - **TODO placeholder for item 003** (line 305)
  - Lines 109-162: _decide_action() LLM function calling (defines "tools" parameter)

- **aorchestra/orchestrator/actions.py:12-31** - Action models
  - Lines 21-23: DelegateAction.tools field (list[str] of tool names)
  - LLM generates tool names, orchestrator must resolve to tool objects

- **aorchestra/core/tuples.py:12-62** - AgentTuple
  - Lines 27-32: tools field receives tool objects from orchestrator
  - Lines 40-48: build_prompt() combines instruction with context

- **aorchestra/core/factory.py:56-62** - Tool validation in factory
  - Validates tools implement Tool protocol
  - ToolRegistry tools should pass this validation

### Test Files (Patterns to Follow)

- **tests/test_tools.py:1-128** - Tool testing patterns
  - Lines 14-27: Test Tool protocol validation
  - Lines 30-49: Test EchoTool functionality
  - Lines 52-95: Test CalculatorTool functionality
  - Async test pattern with pytest.mark.asyncio

- **tests/test_agents.py:65-101** - Tool invocation testing
  - Lines 65-81: Test execute_with_tools
  - Shows how to mock tool calls in OpenAI responses
  - Tests tool execution and result capture

- **tests/test_orchestrator.py:1-163** - Orchestrator testing
  - Lines 98-121: Test _delegate creates tuple and executes
  - Mock-based testing approach for orchestrator methods

### Item Definition

- **.wreckit/items/003-dynamic-context-tool-selection/item.json:1-1** - Item requirements
  - Success criteria: ToolRegistry, tool selection, context curation, 4 built-in tools
  - Line 21: "at least 4 built-in tools: calculator, code_execute, web_search_mock, file_read"
  - Line 23: "Depends on items 001 and 002"
  - Line 25: "Tools must have consistent interface (name, description, execute)"

## Technical Considerations

### Dependencies

**External Dependencies (already installed):**

1. **pydantic>=2.0** - For ToolRegistry and tool metadata models
   - Use for ToolMetadata, ToolRegistry, ToolSelectionStrategy
   - Existing in project (pyproject.toml:5)

2. **typing** - For Protocol and type hints
   - Standard library, already used throughout
   - Protocol for Tool (tools/base.py:12)

3. **asyncio** - For async tool execution
   - Standard library, all tools are async
   - Required by Tool protocol

**Internal Dependencies (from items 001-002):**

1. **Tool protocol** (tools/base.py:12)
   - All built-in tools must implement this
   - ToolRegistry must validate tools on registration

2. **AgentFactory** (core/factory.py)
   - Validated tools in _validate_tuple()
   - ToolRegistry tools should pass validation

3. **Orchestrator** (core/orchestrator.py)
   - _filter_tools() must be replaced
   - _build_context_for_subagent() needs enhancement
   - Integration point for ToolRegistry

4. **AgentTuple** (core/tuples.py)
   - Receives filtered tools
   - Passes to SubAgent

### Patterns to Follow

**From items 001-002:**

1. **Protocol-based tool interface**
   ```python
   @runtime_checkable
   class Tool(Protocol):
       name: str
       description: str
       async def execute(**kwargs) -> Any: ...
   ```

2. **Pydantic models for configuration**
   ```python
   class ToolMetadata(BaseModel):
       name: str
       description: str
       tags: list[str]
       capabilities: list[str]
   ```

3. **Registry pattern**
   ```python
   class ToolRegistry:
       def __init__(self):
           self._tools: dict[str, Tool] = {}

       def register(self, tool: Tool) -> None:
           validate_tool(tool)
           self._tools[tool.name] = tool

       def get(self, name: str) -> Tool | None:
           return self._tools.get(name)

       def select_tools(self, criteria: ToolSelectionCriteria) -> list[Tool]:
           ...
   ```

4. **Async tool execution**
   ```python
   async def execute(self, **kwargs) -> Any:
       # Tool-specific logic
       return result
   ```

5. **Validation functions**
   ```python
   def validate_tool(tool: Any) -> Tool:
       if not isinstance(tool, Tool):
           raise TypeError(...)
       return tool
   ```

6. **Mock-based testing**
   - Mock OpenAI responses for tool call testing
   - Use pytest.mark.asyncio for async tests

**New patterns for item 003:**

1. **Tag-based tool selection**
   - Assign tags to tools (e.g., "math", "code", "web", "file")
   - Select tools by tags based on subtask requirements

2. **Semantic tool matching**
   - Use LLM to analyze subtask and select relevant tools
   - Or use keyword matching with tool descriptions

3. **Context scoring**
   - Score history items by relevance to subtask
   - Select top N most relevant observations

4. **Context summarization**
   - Summarize old observations to save tokens
   - Keep full context for recent history

### Built-in Tools Required

From item.json: "at least 4 built-in tools: calculator, code_execute, web_search_mock, file_read"

1. **CalculatorTool** - ✅ Already exists (tools/mock.py:28-60)
   - Implements add, subtract, multiply, divide
   - Can be enhanced if needed

2. **CodeExecuteTool** - ❌ Needs to be created
   - Execute Python code safely
   - Capture output and errors
   - Return execution result

3. **WebSearchMockTool** - ❌ Needs to be created
   - Mock web search (no real API calls)
   - Return search results from predefined data
   - For testing and demo purposes

4. **FileReadTool** - ❌ Needs to be created
   - Read file contents
   - Handle errors gracefully
   - Support file paths

All tools must implement Tool protocol (name, description, async execute).

## Risks and Mitigations

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| **Tool selection accuracy** | High | LLM may select wrong tools for subtasks. Implement fallback (include all tools if unsure). Test diverse subtasks. Add logging for tool selection decisions. |
| **Context window overflow** | High | Intelligent context curation critical. Summarize old observations. Limit context size (configurable). Prioritize recent + relevant history. |
| **Tool execution errors** | Medium | Tool errors already captured in Observation.error_logs. Add validation before tool registration. Test all built-in tools extensively. |
| **Code execution security** | Medium | CodeExecuteTool must be sandboxed. Use restricted environment. Limit execution time. Disable dangerous operations. |
| **File access security** | Medium | FileReadTool must validate paths. Restrict to safe directories. Prevent directory traversal. Whitelist allowed paths. |
| **Tool registry coupling** | Low | ToolRegistry must integrate cleanly with Orchestrator. Keep interface simple. Add methods only as needed. Don't over-engineer. |
| **Context curation complexity** | Medium | Complex curation logic may introduce bugs. Start simple (keyword matching). Enhance iteratively. Test with diverse delegation histories. |
| **Backward compatibility** | Low | Existing tests may break if _filter_tools() changes. Update tests accordingly. Ensure old test patterns still work. |
| **Mock tool realism** | Low | WebSearchMockTool must provide realistic results. Use curated dataset. Allow customization. Document it's a mock. |
| **Tool metadata management** | Low | ToolMetadata model must be flexible. Use Optional fields. Extensible for future enhancements. |
| **LLM tool selection overhead** | Low | LLM calls for tool selection add latency. Cache selections for similar subtasks. Use simple keyword matching first. |

## Recommended Approach

### High-Level Strategy

Implement ToolRegistry with built-in tools and intelligent selection, then integrate with orchestrator:

**Phase 1: ToolRegistry Foundation**
1. Create ToolMetadata Pydantic model (name, description, tags, capabilities)
2. Create ToolSelectionCriteria model (tags, capabilities, keywords)
3. Implement ToolRegistry class with register(), get(), get_all(), select_tools()
4. Add validation (duplicate names, tool protocol compliance)
5. Write unit tests for registry operations
6. **Verification**: Registry manages tools correctly, validation works

**Phase 2: Built-in Tools Implementation**
1. Enhance CalculatorTool if needed (add metadata, tags)
2. Implement CodeExecuteTool (safe Python execution)
   - Use subprocess or restricted exec
   - Capture stdout/stderr
   - Handle timeouts
3. Implement WebSearchMockTool (mock search results)
   - Predefined search index
   - Return realistic results
   - Support query matching
4. Implement FileReadTool (safe file reading)
   - Path validation
   - Error handling
   - File encoding support
5. Register all tools in registry with metadata
6. Write tests for each tool (async execution, error handling)
7. **Verification**: All 4 tools implement Tool protocol, execute correctly

**Phase 3: Tool Selection Logic**
1. Implement tag-based selection in ToolRegistry
2. Implement keyword matching (match keywords to tool descriptions)
3. Implement LLM-based selection (optional, for complex subtasks)
4. Add fallback (include all tools if unsure)
5. Write tests for selection logic
6. **Verification**: Tool selection returns relevant tools for diverse criteria

**Phase 4: Orchestrator Integration**
1. Replace Orchestrator._filter_tools() with ToolRegistry-based implementation
   - Instantiate ToolRegistry in __init__
   - Register built-in tools
   - Update _filter_tools() to use registry.select_tools()
2. Enhance Orchestrator._build_context_for_subagent()
   - Score history items by relevance (keyword matching)
   - Select top N most relevant observations
   - Summarize old observations if needed
3. Update Orchestrator.__init__ to accept ToolRegistry (optional)
4. Write integration tests with orchestrator
5. **Verification**: Orchestrator selects correct tools, context is relevant

**Phase 5: End-to-End Testing**
1. Create integration tests with real LLM
2. Test diverse subtasks (math, code, research)
3. Verify tool selection per subtask
4. Verify context curation effectiveness
5. Test error handling (missing tools, invalid files)
6. **Verification**: Full workflow with intelligent tool/context selection

### Architectural Decisions

1. **Package Structure:**
   ```
   aorchestra/
   ├── tools/
   │   ├── base.py          # (existing) Tool protocol
   │   ├── mock.py          # (existing) EchoTool, CalculatorTool, ErrorTool
   │   ├── registry.py      # (NEW) ToolRegistry, ToolMetadata
   │   ├── builtins.py      # (NEW) CodeExecuteTool, WebSearchMockTool, FileReadTool
   │   ├── selection.py     # (NEW) ToolSelectionCriteria, selection logic
   │   └── __init__.py      # Export ToolRegistry, built-in tools
   ├── core/
   │   └── orchestrator.py  # (MODIFY) Replace _filter_tools(), enhance _build_context_for_subagent()
   └── orchestrator/
       └── context.py       # (NEW) Context curation logic
   ```

2. **ToolMetadata Model:**
   ```python
   class ToolMetadata(BaseModel):
       name: str
       description: str
       tags: list[str] = Field(default_factory=list)
       capabilities: list[str] = Field(default_factory=list)
       requires_sandbox: bool = False
   ```

3. **ToolRegistry Class:**
   ```python
   class ToolRegistry:
       def __init__(self):
           self._tools: dict[str, Tool] = {}
           self._metadata: dict[str, ToolMetadata] = {}

       def register(self, tool: Tool, metadata: ToolMetadata) -> None:
           validate_tool(tool)
           if tool.name in self._tools:
               raise ValueError(f"Tool {tool.name} already registered")
           self._tools[tool.name] = tool
           self._metadata[tool.name] = metadata

       def get(self, name: str) -> Tool | None:
           return self._tools.get(name)

       def get_all(self) -> list[Tool]:
           return list(self._tools.values())

       def select_tools(self, criteria: ToolSelectionCriteria) -> list[Tool]:
           # Tag matching, keyword matching, capability filtering
           selected = []
           for tool in self.get_all():
               metadata = self._metadata[tool.name]
               if self._matches_criteria(metadata, criteria):
                   selected.append(tool)
           return selected
   ```

4. **Built-in Tools:**
   - CalculatorTool (existing, enhance with metadata)
   - CodeExecuteTool (sandboxed Python execution)
   - WebSearchMockTool (predefined search results)
   - FileReadTool (safe file reading)

5. **Tool Selection Strategies:**
   ```python
   class ToolSelectionCriteria(BaseModel):
       tags: list[str] = Field(default_factory=list)
       capabilities: list[str] = Field(default_factory=list)
       keywords: list[str] = Field(default_factory=list)
       max_tools: int = 10
   ```

6. **Context Curation:**
   ```python
   def score_relevance(text: str, keywords: list[str]) -> float:
       # Score by keyword frequency
       score = sum(text.lower().count(kw.lower()) for kw in keywords)
       return score

   def select_relevant_history(
       history: list[Delegation],
       keywords: list[str],
       max_items: int = 5
   ) -> list[Delegation]:
       scored = [(d, score_relevance(d.observation.result_summary, keywords))
                 for d in history]
       scored.sort(key=lambda x: x[1], reverse=True)
       return [d for d, score in scored[:max_items]]
   ```

7. **Orchestrator Integration:**
   ```python
   # In __init__:
   self.tool_registry = ToolRegistry()
   self._register_builtin_tools()

   def _register_builtin_tools(self):
       calculator = CalculatorTool()
       calculator_meta = ToolMetadata(
           name=calculator.name,
           description=calculator.description,
           tags=["math", "calculation"],
           capabilities=["arithmetic"]
       )
       self.tool_registry.register(calculator, calculator_meta)
       # ... register other tools

   # Replace _filter_tools():
   def _filter_tools(self, tool_names: list[str]) -> list[Tool]:
       # If LLM specified tool names, get those tools
       if tool_names:
           tools = []
           for name in tool_names:
               tool = self.tool_registry.get(name)
               if tool:
                   tools.append(tool)
           return tools

       # Otherwise, select based on task keywords (intelligent)
       keywords = self._extract_keywords_from_task()
       criteria = ToolSelectionCriteria(keywords=keywords)
       return self.tool_registry.select_tools(criteria)
   ```

### Implementation Order

Priority order based on dependencies and complexity:

1. **ToolRegistry foundation** (tools/registry.py)
   - No dependencies, core infrastructure
   - Pydantic models for metadata

2. **Built-in tools** (tools/builtins.py)
   - CodeExecuteTool, WebSearchMockTool, FileReadTool
   - CalculatorTool enhancement
   - Independent, parallel development possible

3. **Tool selection logic** (tools/selection.py)
   - Depends on ToolRegistry
   - Tag-based, keyword-based, LLM-based selection

4. **Context curation** (orchestrator/context.py)
   - Independent module
   - Relevance scoring, history selection

5. **Orchestrator integration** (core/orchestrator.py)
   - Replace _filter_tools()
   - Enhance _build_context_for_subagent()
   - Integrate ToolRegistry

6. **Testing** (tests/test_tools.py, tests/test_orchestrator.py)
   - Parallel with implementation
   - Unit tests first, integration tests last

### Testing Strategy

Follow items 001-002 testing patterns:

1. **Unit Tests (ToolRegistry):**
   - Test tool registration (valid, duplicate names)
   - Test tool retrieval (get, get_all)
   - Test tool selection (tags, keywords, capabilities)
   - Test validation (protocol compliance)

2. **Unit Tests (Built-in Tools):**
   - Test CalculatorTool (already tested in test_tools.py)
   - Test CodeExecuteTool (valid code, errors, timeouts)
   - Test WebSearchMockTool (queries, results)
   - Test FileReadTool (valid paths, errors, permissions)
   - All tests async with pytest.mark.asyncio

3. **Unit Tests (Context Curation):**
   - Test relevance scoring
   - Test history selection
   - Test summarization (if implemented)

4. **Integration Tests (Orchestrator):**
   - Test _filter_tools() with ToolRegistry
   - Test _build_context_for_subagent() with curation
   - Mock LLM for deterministic tests
   - Test tool selection per subtask

5. **End-to-End Tests:**
   - Test full workflow with real LLM
   - Test diverse subtasks (math, code, research)
   - Verify tool selection correctness
   - Verify context relevance

## Open Questions

**Clarifications needed:**

1. **Code execution sandboxing** - Should CodeExecuteTool use:
   - subprocess with timeout (simpler, more isolated)?
   - restricted exec (more flexible, less secure)?
   - docker container (most secure, most complex)?
   - Decision: Start with subprocess + timeout, enhance if needed.

2. **Web search realism** - Should WebSearchMockTool:
   - Use static predefined results (simpler)?
   - Dynamic results based on query matching?
   - Interface to real search API (optional)?
   - Decision: Use static predefined results with query keyword matching.

3. **Context summarization** - Should old observations be:
   - Summarized using LLM (more accurate, more expensive)?
   - Truncated to N characters (simpler, less accurate)?
   - Kept full with window limit (simplest)?
   - Decision: Keep full with window limit initially, add summarization later if needed.

4. **Tool selection strategy** - Should tool selection be:
   - Purely tag/keyword-based (deterministic)?
   - LLM-assisted (more intelligent, slower)?
   - Hybrid (keywords first, LLM for complex tasks)?
   - Decision: Hybrid approach - keyword matching by default, LLM for complex subtasks.

5. **ToolRegistry initialization** - Should registry be:
   - Created in Orchestrator.__init__ (tightly coupled)?
   - Passed as dependency (more flexible)?
   - Global singleton (simpler, less testable)?
   - Decision: Dependency injection - accept ToolRegistry in __init__, create default if None.

6. **Context curation integration** - Should context curation:
   - Replace _build_context_for_subagent() entirely?
   - Add helper methods to Orchestrator?
   - Separate module with integration hooks?
   - Decision: Create separate orchestrator/context.py module, integrate via methods.

**Decisions to be made during implementation:**
- Code execution sandbox approach
- Web search mock data structure
- Context summarization strategy
- Tool selection fallback behavior
- Error handling for missing tools

These can be addressed iteratively during implementation with the flexible architecture outlined above.
