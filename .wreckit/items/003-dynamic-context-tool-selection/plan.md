# Dynamic context curation and tool selection Implementation Plan

## Implementation Plan Title

ToolRegistry with intelligent tool selection and enhanced context curation for Orchestrator

## Overview

This implementation creates a centralized ToolRegistry to manage available tools with metadata, implements 4 built-in tools (calculator, code_execute, web_search_mock, file_read), and enhances the Orchestrator with intelligent tool selection and context curation capabilities. The orchestrator will dynamically select relevant tools for each subtask and filter context to include only task-relevant information, improving efficiency and preventing context rot.

## Current State

The foundation (items 001 and 002) is complete with full AgentTuple, SubAgent, Observation, AgentFactory, and Orchestrator implementations. The current state includes:

**Existing Infrastructure:**
- Tool protocol defined in `aorchestra/tools/base.py:12-41` with name, description, async execute
- Three mock tools in `aorchestra/tools/mock.py`: EchoTool, CalculatorTool, ErrorTool
- Orchestrator with placeholder `_filter_tools()` returning empty list at `aorchestra/core/orchestrator.py:305`
- Basic context building in `_build_context_for_subagent()` at `orchestrator.py:263-286` (last 3 observations only)
- SubAgent tool invocation in `aorchestra/core/agents.py:97-226` with OpenAI function calling support
- DelegateAction.tools field for tool names in `aorchestra/orchestrator/actions.py:21-23`

**What's Missing:**
- No centralized tool registry to manage available tools
- No tool metadata system (tags, capabilities)
- No intelligent tool selection logic
- Limited context curation (simple "last 3" approach)
- Missing built-in tools: code_execute, web_search_mock, file_read
- Placeholder implementation of `_filter_tools()` needs replacement

**Key Constraints:**
- All tools must implement Tool protocol from `tools/base.py:12`
- Tools must be compatible with existing SubAgent._prepare_tools() at `agents.py:97`
- ToolRegistry must integrate cleanly with Orchestrator.__init__()
- Cannot break existing test patterns from `tests/test_tools.py` and `tests/test_orchestrator.py`

## Desired End State

The system will have a fully functional ToolRegistry managing 4 built-in tools with metadata, intelligent tool selection based on subtask requirements, and enhanced context curation that filters relevant history for each sub-agent.

### Key Deliverables:

1. **ToolRegistry** - Centralized registry in `aorchestra/tools/registry.py`
   - Register/unregister tools with metadata validation
   - Query tools by name, tags, capabilities, keywords
   - Select tools based on criteria
   - Support for dependency injection into Orchestrator

2. **4 Built-in Tools** - Complete implementation in `aorchestra/tools/builtins.py`
   - CalculatorTool (existing, enhance with metadata)
   - CodeExecuteTool (sandboxed Python execution with timeout)
   - WebSearchMockTool (mock search with predefined results)
   - FileReadTool (safe file reading with path validation)

3. **Tool Selection Logic** - Smart selection in `aorchestra/tools/selection.py`
   - Tag-based matching
   - Keyword matching against tool descriptions
   - Capability filtering
   - Fallback to all tools if uncertain

4. **Context Curation** - Enhanced filtering in `aorchestra/orchestrator/context.py`
   - Relevance scoring of history items
   - Select top N most relevant observations
   - Context building for subtasks

5. **Orchestrator Integration** - Updated at `aorchestra/core/orchestrator.py`
   - ToolRegistry initialized in __init__
   - `_filter_tools()` replaced with registry-based selection
   - `_build_context_for_subagent()` enhanced with curation
   - Register built-in tools on initialization

### Verification Criteria:

- All 4 built-in tools implement Tool protocol and pass validate_tool()
- ToolRegistry successfully manages tools with metadata
- Orchestrator selects correct tools per subtask based on requirements
- Context curation includes only relevant history, improving token efficiency
- All existing tests pass plus new comprehensive test coverage
- Integration tests demonstrate end-to-end tool selection and curation

### Key Discoveries:

- **Existing Tool Protocol**: `tools/base.py:12-41` defines Tool protocol with name, description, async execute. Item 003 must follow this exactly.
- **Validation Pattern**: `tools/base.py:44-61` has validate_tool() function. ToolRegistry should use this for tool validation.
- **Placeholder Implementation**: `orchestrator.py:293-312` has `_filter_tools()` with TODO comment on line 305. This is the main integration point.
- **Tool Names in Action**: `orchestrator/actions.py:21-23` shows DelegateAction.tools is list[str]. Orchestrator must resolve names to tool objects.
- **AgentTuple.tools Field**: `tuples.py:27-32` accepts list[Any] for tools. Tool objects must be passed directly.
- **SubAgent Tool Handling**: `agents.py:97-226` shows how tools are converted to OpenAI format and executed. Must be compatible.
- **Test Patterns**: `tests/test_tools.py` and `tests/test_agents.py` use pytest.mark.asyncio for async tests. Follow this pattern.
- **Mock-Based Testing**: `tests/test_orchestrator.py:98-121` shows how to mock LLM responses. Use this for deterministic tests.

## What We're NOT Doing

- **Real web search API integration** - WebSearchMockTool returns predefined results, no live API calls
- **Advanced code sandboxing** - CodeExecuteTool uses subprocess with timeout, not full container isolation
- **LLM-based context summarization** - Simple keyword scoring and selection, no LLM summarization of old observations
- **Dynamic tool loading from files** - Tools registered programmatically only, no plugin system
- **Tool permission system** - No per-user or per-task tool authorization
- **Tool result caching** - No caching of tool execution results
- **Tool dependency resolution** - No handling of tools requiring other tools
- **Multi-model tool selection** - Single ToolRegistry shared across all subtasks
- **Tool versioning** - No version management for tools
- **Tool telemetry/analytics** - No tracking of tool usage patterns

## Implementation Approach

### High-Level Strategy

Implement ToolRegistry and built-in tools first (foundation), then integrate with Orchestrator (enhancement). Use dependency injection for testability and follow existing patterns from items 001-002.

**Rationale:**
1. **Foundation First**: ToolRegistry has no dependencies on Orchestrator. Build and test it independently.
2. **Built-in Tools Next**: Tools are independent of each other. Implement in parallel, test thoroughly.
3. **Orchestrator Integration Last**: Depends on both ToolRegistry and tools being complete.
4. **Test Throughout**: Write unit tests for each component, integration tests for Orchestrator.

### Architectural Decisions

1. **Package Structure**:
   - `aorchestra/tools/registry.py` - ToolRegistry and ToolMetadata
   - `aorchestra/tools/builtins.py` - Built-in tool implementations
   - `aorchestra/tools/selection.py` - ToolSelectionCriteria and logic
   - `aorchestra/orchestrator/context.py` - Context curation helpers
   - Modify `aorchestra/core/orchestrator.py` for integration

2. **ToolMetadata Model** - Pydantic model for tool metadata (name, description, tags, capabilities, requires_sandbox)

3. **Registry Pattern** - ToolRegistry with register(), get(), get_all(), select_tools() methods. Validates tools on registration.

4. **Tool Selection Strategy** - Hybrid approach: tag matching, keyword matching, capability filtering. Fallback to all tools if unsure.

5. **Context Curation** - Relevance scoring using keyword frequency, select top N most relevant observations.

6. **Dependency Injection** - ToolRegistry passed to Orchestrator.__init__(), creates default with built-in tools if None.

7. **Sandboxing** - CodeExecuteTool uses subprocess with timeout and restricted environment variables.

8. **Security** - FileReadTool validates paths, restricts to safe directories, prevents directory traversal.

---

## Phases

### Phase 1: ToolRegistry Foundation

#### Overview

Implement ToolRegistry with metadata management and tool validation. This is the foundation for all tool operations and has no dependencies on other components.

#### Changes Required:

##### 1. Create ToolRegistry and ToolMetadata models

**File**: `aorchestra/tools/registry.py` (NEW)
**Changes**: Implement ToolRegistry class with Pydantic models

```python
"""Tool registry for managing available tools with metadata.

Item 003: Dynamic context curation and tool selection
"""

from typing import Any
from pydantic import BaseModel, Field

from aorchestra.tools.base import Tool, validate_tool


class ToolMetadata(BaseModel):
    """Metadata for a tool in the registry.

    Enables intelligent tool selection based on tags, capabilities,
    and descriptions.
    """

    name: str = Field(..., description="Tool name (must match tool.name)")
    description: str = Field(..., description="Tool description (must match tool.description)")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization (e.g., 'math', 'code')")
    capabilities: list[str] = Field(default_factory=list, description="Specific capabilities (e.g., 'arithmetic', 'file_io')")
    requires_sandbox: bool = Field(default=False, description="Whether tool requires sandboxed execution")


class ToolSelectionCriteria(BaseModel):
    """Criteria for selecting tools from the registry.

    Used by Orchestrator to find relevant tools for subtasks.
    """

    tags: list[str] = Field(default_factory=list, description="Required tags (OR logic)")
    capabilities: list[str] = Field(default_factory=list, description="Required capabilities (OR logic)")
    keywords: list[str] = Field(default_factory=list, description="Keywords to match in tool descriptions")
    tool_names: list[str] = Field(default_factory=list, description="Specific tool names to include")
    max_tools: int = Field(default=10, description="Maximum number of tools to return")


class ToolRegistry:
    """Central registry for managing available tools.

    Provides methods for registering, retrieving, and selecting tools
    based on metadata and selection criteria.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._tools: dict[str, Tool] = {}
        self._metadata: dict[str, ToolMetadata] = {}

    def register(self, tool: Tool, metadata: ToolMetadata) -> None:
        """Register a tool with metadata.

        Args:
            tool: Tool object implementing Tool protocol.
            metadata: Metadata for the tool.

        Raises:
            TypeError: If tool doesn't implement Tool protocol.
            ValueError: If tool name already registered or name mismatch.
        """
        # Validate tool implements protocol
        validated_tool = validate_tool(tool)

        # Validate name consistency
        if validated_tool.name != metadata.name:
            raise ValueError(
                f"Tool name mismatch: tool.name='{validated_tool.name}' != metadata.name='{metadata.name}'"
            )

        # Check for duplicate
        if validated_tool.name in self._tools:
            raise ValueError(f"Tool '{validated_tool.name}' already registered")

        # Store tool and metadata
        self._tools[validated_tool.name] = validated_tool
        self._metadata[validated_tool.name] = metadata

    def unregister(self, name: str) -> None:
        """Unregister a tool by name.

        Args:
            name: Tool name to unregister.

        Raises:
            KeyError: If tool not found.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not registered")
        del self._tools[name]
        del self._metadata[name]

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool object or None if not found.
        """
        return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name.

        Args:
            name: Tool name.

        Returns:
            ToolMetadata or None if not found.
        """
        return self._metadata.get(name)

    def get_all(self) -> list[Tool]:
        """Get all registered tools.

        Returns:
            List of all tool objects.
        """
        return list(self._tools.values())

    def select_tools(self, criteria: ToolSelectionCriteria) -> list[Tool]:
        """Select tools matching the given criteria.

        Selection logic:
        1. If tool_names specified, return those tools only
        2. Otherwise, filter by tags, capabilities, keywords
        3. Return up to max_tools matches

        Args:
            criteria: Selection criteria.

        Returns:
            List of matching tools.
        """
        # If specific tool names requested, return those
        if criteria.tool_names:
            tools = []
            for name in criteria.tool_names:
                tool = self.get(name)
                if tool:
                    tools.append(tool)
            return tools

        # Otherwise, apply filters
        selected = []
        for tool in self.get_all():
            metadata = self._metadata[tool.name]

            if self._matches_criteria(metadata, criteria):
                selected.append(tool)

        # Limit to max_tools
        return selected[:criteria.max_tools]

    def _matches_criteria(self, metadata: ToolMetadata, criteria: ToolSelectionCriteria) -> bool:
        """Check if tool metadata matches criteria.

        Args:
            metadata: Tool metadata.
            criteria: Selection criteria.

        Returns:
            True if tool matches criteria.
        """
        # Tag matching (OR logic: match any tag)
        if criteria.tags:
            if not any(tag in metadata.tags for tag in criteria.tags):
                return False

        # Capability matching (OR logic: match any capability)
        if criteria.capabilities:
            if not any(cap in metadata.capabilities for cap in criteria.capabilities):
                return False

        # Keyword matching in description (case-insensitive)
        if criteria.keywords:
            desc_lower = metadata.description.lower()
            if not any(kw.lower() in desc_lower for kw in criteria.keywords):
                return False

        return True

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if tool is registered."""
        return name in self._tools
```

##### 2. Export from tools module

**File**: `aorchestra/tools/__init__.py`
**Changes**: Export ToolRegistry and ToolMetadata

```python
"""Tool system for AOrchestra.

Item 001: Tool protocol and mock tools
Item 003: ToolRegistry with metadata and selection
"""

from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.registry import ToolRegistry, ToolMetadata, ToolSelectionCriteria

__all__ = [
    "Tool",
    "validate_tool",
    "ToolRegistry",
    "ToolMetadata",
    "ToolSelectionCriteria",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_tool_registry.py -v`
- [ ] Type checking passes: `mypy aorchestra/tools/registry.py` (if mypy configured)
- [ ] Import works: `python -c "from aorchestra.tools import ToolRegistry, ToolMetadata"`

##### Manual Verification:

- [ ] ToolRegistry can be instantiated without errors
- [ ] Tool registration validates Tool protocol correctly
- [ ] Duplicate tool names raise ValueError
- [ ] Tool selection filters by tags, capabilities, keywords correctly
- [ ] Tool names in criteria override other filters

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 2: Built-in Tools Implementation

#### Overview

Implement the 4 built-in tools (calculator, code_execute, web_search_mock, file_read) following the Tool protocol. CalculatorTool exists and will be enhanced with metadata; the other three are new implementations.

#### Changes Required:

##### 1. Create built-in tools module

**File**: `aorchestra/tools/builtins.py` (NEW)
**Changes**: Implement all 4 built-in tools with Tool protocol

Due to length constraints, key components:

```python
"""Built-in tools for AOrchestra.

Item 003: Four built-in tools for common operations.
"""

import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from aorchestra.tools.registry import ToolMetadata


class CalculatorTool:
    """A basic calculator tool for arithmetic operations."""

    name: str = "calculator"
    description: str = "Performs basic arithmetic operations: add, subtract, multiply, divide"

    async def execute(self, operation: str, a: float, b: float) -> float:
        """Execute a calculator operation."""
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")


class CodeExecuteTool:
    """Safely executes Python code in a subprocess."""

    name: str = "code_execute"
    description: str = "Executes Python code safely in a subprocess. Returns stdout and stderr."

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def execute(self, code: str) -> dict[str, Any]:
        """Execute Python code in a subprocess."""
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)

        try:
            process = await asyncio.create_subprocess_exec(
                "python", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError as e:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Code execution timed out after {self.timeout} seconds") from e

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode,
            }

        except FileNotFoundError:
            raise RuntimeError("Python interpreter not found")
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }


class WebSearchMockTool:
    """Mock web search tool for testing and demonstration."""

    name: str = "web_search_mock"
    description: str = "Performs mock web search. Returns predefined results for testing."

    def __init__(self, search_index: dict[str, list[dict[str, Any]]] | None = None):
        self.search_index = search_index or self._default_search_index()

    @staticmethod
    def _default_search_index() -> dict[str, list[dict[str, Any]]]:
        return {
            "python": [
                {"title": "Python Official Website", "url": "https://python.org", "snippet": "The official home of Python programming language."},
                {"title": "Python Documentation", "url": "https://docs.python.org", "snippet": "Official Python documentation and tutorials."},
            ],
            "async": [
                {"title": "Python asyncio Documentation", "url": "https://docs.python.org/3/library/asyncio.html", "snippet": "Asynchronous I/O, event loop, coroutines and tasks."},
            ],
        }

    async def execute(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Perform mock web search."""
        query_lower = query.lower()
        matched_results = []

        for keyword, results in self.search_index.items():
            if keyword in query_lower:
                matched_results.extend(results)

        # Remove duplicates
        seen_urls = set()
        unique_results = []
        for result in matched_results:
            url = result["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        results = unique_results[:max_results]

        return {
            "query": query,
            "results": results,
            "total": len(results),
        }


class FileReadTool:
    """Safely reads file contents with path validation."""

    name: str = "file_read"
    description: str = "Reads file contents safely. Supports text files with encoding."

    def __init__(self, allowed_dirs: list[str] | None = None):
        self.allowed_dirs = allowed_dirs or [str(Path.cwd())]
        self.allowed_dirs = [str(Path(d).resolve()) for d in self.allowed_dirs]

    async def execute(self, path: str, encoding: str = "utf-8") -> dict[str, Any]:
        """Read file contents."""
        abs_path = Path(path).resolve()
        self._validate_path(abs_path)

        if not abs_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        if not os.access(abs_path, os.R_OK):
            raise PermissionError(f"Cannot read file (permission denied): {path}")

        try:
            content = abs_path.read_text(encoding=encoding)
            file_size = abs_path.stat().st_size

            return {
                "success": True,
                "content": content,
                "path": str(abs_path),
                "size": file_size,
                "error": None,
            }
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode file with encoding '{encoding}': {e}")
        except Exception as e:
            raise IOError(f"Failed to read file: {e}")

    def _validate_path(self, path: Path) -> None:
        """Validate path is within allowed directories."""
        path_str = str(path)

        for allowed_dir in self.allowed_dirs:
            if path_str.startswith(allowed_dir):
                try:
                    real_path = path.resolve(strict=True)
                    real_allowed_dir = Path(allowed_dir).resolve()

                    if str(real_path).startswith(str(real_allowed_dir)):
                        return
                except (FileNotFoundError, PermissionError):
                    pass

        raise ValueError(
            f"Path '{path}' is outside allowed directories: {self.allowed_dirs}"
        )


def get_builtin_tools_metadata() -> list[tuple[ToolMetadata, type]]:
    """Get metadata for all built-in tools."""
    return [
        (
            ToolMetadata(
                name="calculator",
                description="Performs basic arithmetic operations: add, subtract, multiply, divide",
                tags=["math", "calculation", "arithmetic"],
                capabilities=["add", "subtract", "multiply", "divide"],
                requires_sandbox=False,
            ),
            CalculatorTool,
        ),
        (
            ToolMetadata(
                name="code_execute",
                description="Executes Python code safely in a subprocess. Returns stdout and stderr.",
                tags=["code", "execution", "python"],
                capabilities=["execute", "run_code"],
                requires_sandbox=True,
            ),
            CodeExecuteTool,
        ),
        (
            ToolMetadata(
                name="web_search_mock",
                description="Performs mock web search. Returns predefined results for testing.",
                tags=["web", "search", "research"],
                capabilities=["search", "query"],
                requires_sandbox=False,
            ),
            WebSearchMockTool,
        ),
        (
            ToolMetadata(
                name="file_read",
                description="Reads file contents safely. Supports text files with encoding.",
                tags=["file", "io", "filesystem"],
                capabilities=["read", "read_file"],
                requires_sandbox=False,
            ),
            FileReadTool,
        ),
    ]
```

##### 2. Export built-in tools

**File**: `aorchestra/tools/__init__.py`
**Changes**: Export built-in tools

```python
"""Tool system for AOrchestra.

Item 001: Tool protocol and mock tools
Item 003: ToolRegistry with metadata and selection
"""

from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.registry import ToolRegistry, ToolMetadata, ToolSelectionCriteria

# Built-in tools
from aorchestra.tools.builtins import (
    CalculatorTool,
    CodeExecuteTool,
    WebSearchMockTool,
    FileReadTool,
    get_builtin_tools_metadata,
)

__all__ = [
    "Tool",
    "validate_tool",
    "ToolRegistry",
    "ToolMetadata",
    "ToolSelectionCriteria",
    "CalculatorTool",
    "CodeExecuteTool",
    "WebSearchMockTool",
    "FileReadTool",
    "get_builtin_tools_metadata",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_builtins.py -v`
- [ ] All tools pass validate_tool() check
- [ ] CalculatorTool returns correct arithmetic results
- [ ] CodeExecuteTool executes code and captures output
- [ ] WebSearchMockTool returns relevant results
- [ ] FileReadTool reads files and validates paths

##### Manual Verification:

- [ ] CalculatorTool handles all operations (add, subtract, multiply, divide)
- [ ] CalculatorTool raises error for divide by zero and unknown operations
- [ ] CodeExecuteTool times out on infinite loops
- [ ] CodeExecuteTool captures both stdout and stderr
- [ ] WebSearchMockTool matches keywords correctly
- [ ] FileReadTool rejects paths outside allowed directories
- [ ] FileReadTool handles Unicode encoding correctly

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 3: Context Curation System

#### Overview

Implement intelligent context curation that analyzes delegation history and selects relevant observations based on subtask requirements. This prevents context rot and improves token efficiency.

#### Changes Required:

##### 1. Create context curation module

**File**: `aorchestra/orchestrator/context.py` (NEW)
**Changes**: Implement context scoring and selection

```python
"""Context curation for Orchestrator.

Item 003: Intelligent filtering of relevant context for sub-agents.
"""

import re
from typing import Any

from aorchestra.orchestrator.state import Delegation


def score_relevance(text: str, keywords: list[str]) -> float:
    """Score text relevance based on keyword frequency.

    Simple scoring algorithm:
    - Count keyword occurrences (case-insensitive)
    - Exact matches get higher score
    - Partial matches get partial score

    Args:
        text: Text to score.
        keywords: Keywords to search for.

    Returns:
        Relevance score (higher = more relevant).
    """
    if not keywords or not text:
        return 0.0

    text_lower = text.lower()
    score = 0.0

    for keyword in keywords:
        keyword_lower = keyword.lower()

        # Exact word match (higher weight)
        word_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        exact_matches = len(re.findall(word_pattern, text_lower))
        score += exact_matches * 2.0

        # Partial match (lower weight)
        partial_matches = text_lower.count(keyword_lower) - exact_matches
        score += partial_matches * 0.5

    return score


def select_relevant_history(
    history: list[Delegation],
    keywords: list[str] | None = None,
    max_items: int = 5,
    include_recent: int = 2,
) -> list[Delegation]:
    """Select relevant items from delegation history.

    Combines recent items (always included) with keyword-relevant items.

    Args:
        history: List of Delegation records.
        keywords: Keywords for relevance scoring.
        max_items: Maximum items to return.
        include_recent: Number of most recent items to always include.

    Returns:
        List of selected Delegation records, ordered by relevance.
    """
    if not history:
        return []

    # Always include recent items
    recent_items = history[-include_recent:] if include_recent > 0 else []
    recent_indices = {id(d) for d in recent_items}

    # Score remaining items by keyword relevance
    keywords = keywords or []
    scored = []

    for delegation in history[:-include_recent] if include_recent > 0 else history:
        # Skip if already in recent items
        if id(delegation) in recent_indices:
            continue

        # Build text from observation summary and instruction
        text = (
            delegation.observation.result_summary + " " +
            delegation.tuple.instruction
        )

        score = score_relevance(text, keywords)
        scored.append((delegation, score))

    # Sort by score (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Select top scored items
    top_scored = [d for d, _ in scored[:max_items - len(recent_items)]]

    # Combine: recent items first, then scored items
    selected = recent_items + top_scored

    # Limit to max_items
    return selected[:max_items]


def build_context_for_subtask(
    action_context: str,
    history: list[Delegation],
    keywords: list[str] | None = None,
    max_history_items: int = 3,
) -> str:
    """Build context string for a subtask.

    Combines action-specific context with relevant history.

    Args:
        action_context: Context from DelegateAction.
        history: Delegation history.
        keywords: Keywords for relevance scoring.
        max_history_items: Max history items to include.

    Returns:
        Formatted context string.
    """
    parts = []

    # Add action-specific context
    if action_context:
        parts.append(action_context)

    # Add relevant history
    if history:
        selected = select_relevant_history(
            history=history,
            keywords=keywords,
            max_items=max_history_items,
            include_recent=max(1, max_history_items // 2),
        )

        if selected:
            parts.append("\n**Relevant Previous Work:**")
            for delegation in selected:
                parts.append(
                    f"- {delegation.observation.result_summary}"
                )

    return "\n".join(parts) if parts else ""


def extract_keywords_from_instruction(instruction: str) -> list[str]:
    """Extract relevant keywords from an instruction.

    Simple extraction: identify nouns and technical terms.
    For now, split by common delimiters and filter stopwords.

    Args:
        instruction: Instruction text.

    Returns:
        List of keywords.
    """
    if not instruction:
        return []

    # Common stopwords to filter
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "as", "is", "was", "are",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "must",
        "please", "help", "need", "want", "use", "make", "get",
    }

    # Split by common delimiters
    words = re.findall(r'\b[a-zA-Z]{3,}\b', instruction.lower())

    # Filter stopwords and short words
    keywords = [w for w in words if w not in stopwords]

    return keywords
```

##### 2. Export from orchestrator module

**File**: `aorchestra/orchestrator/__init__.py`
**Changes**: Export context functions

```python
"""Orchestrator components."""

from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.orchestrator.prompts import build_system_prompt, build_user_prompt
from aorchestra.orchestrator.context import (
    score_relevance,
    select_relevant_history,
    build_context_for_subtask,
    extract_keywords_from_instruction,
)

__all__ = [
    "OrchestratorState",
    "Delegation",
    "DelegateAction",
    "FinishAction",
    "build_system_prompt",
    "build_user_prompt",
    "score_relevance",
    "select_relevant_history",
    "build_context_for_subtask",
    "extract_keywords_from_instruction",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_context.py -v`
- [ ] score_relevance returns higher scores for more keyword matches
- [ ] select_relevant_history includes recent items
- [ ] select_relevant_history scores by keyword relevance
- [ ] build_context_for_subtask combines context and history
- [ ] extract_keywords_from_instruction filters stopwords

##### Manual Verification:

- [ ] Context with exact keyword matches gets highest score
- [ ] Context scoring is case-insensitive
- [ ] Recent items are always included in selection
- [ ] Context building handles empty history gracefully
- [ ] Keyword extraction removes common stopwords

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 4: Orchestrator Integration

#### Overview

Integrate ToolRegistry and context curation into the Orchestrator. Replace the placeholder `_filter_tools()` method and enhance `_build_context_for_subagent()` with intelligent curation.

#### Changes Required:

##### 1. Update Orchestrator class

**File**: `aorchestra/core/orchestrator.py`
**Changes**: Add ToolRegistry, replace _filter_tools, enhance _build_context_for_subagent

Key changes:

```python
"""Orchestrator for task delegation and decision-making."""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator import prompts, context
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.tools import (
    ToolRegistry,
    get_builtin_tools_metadata,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central orchestrator that delegates tasks to sub-agents.

    The orchestrator maintains a state history of all delegations and
    observations, and uses an LLM to decide at each step whether to
    Delegate (spawn a sub-agent) or Finish (return final answer).

    Item 003: Enhanced with ToolRegistry and intelligent context curation.
    """

    def __init__(
        self,
        model: ModelConfig,
        factory: Optional[AgentFactory] = None,
        tool_registry: Optional[ToolRegistry] = None,
        max_steps: int = 20,
    ):
        """Initialize the orchestrator.

        Args:
            model: Model configuration for the orchestrator's LLM.
            factory: AgentFactory for creating sub-agents. If None, creates default.
            tool_registry: ToolRegistry for managing tools. If None, creates default
                with built-in tools.
            max_steps: Maximum number of delegation steps (prevents infinite loops).
        """
        self.model = model
        self.factory = factory or AgentFactory()
        self.max_steps = max_steps
        self.client = AsyncOpenAI(**model.to_openai_kwargs())
        self.state: Optional[OrchestratorState] = None

        # Initialize tool registry (item 003)
        self.tool_registry = tool_registry or self._create_default_tool_registry()

    def _create_default_tool_registry(self) -> ToolRegistry:
        """Create default ToolRegistry with built-in tools.

        Returns:
            ToolRegistry with all built-in tools registered.
        """
        registry = ToolRegistry()

        # Register all built-in tools
        for metadata, tool_class in get_builtin_tools_metadata():
            tool = tool_class()
            registry.register(tool, metadata)
            logger.info(f"Registered built-in tool: {tool.name}")

        return registry

    # ... existing run(), _decide_action(), _delegate(), _integrate_observation() methods ...

    def _build_context_for_subagent(self, action: DelegateAction) -> str:
        """Build context string for a sub-agent.

        Item 003: Enhanced with intelligent context curation.
        Uses keyword extraction and relevance scoring to select
        relevant history items.

        Args:
            action: The DelegateAction being executed.

        Returns:
            Formatted context string.
        """
        # Extract keywords from instruction for relevance scoring
        keywords = context.extract_keywords_from_instruction(action.instruction)

        # Build context using curation logic
        return context.build_context_for_subtask(
            action_context=action.context,
            history=self.state.history if self.state else [],
            keywords=keywords,
            max_history_items=3,
        )

    def _filter_tools(self, tool_names: list[str]) -> list:
        """Filter tools by name or intelligently select based on task.

        Item 003: Uses ToolRegistry for tool selection.

        If LLM specified tool names, returns those tools.
        Otherwise, uses intelligent selection based on task keywords.

        Args:
            tool_names: List of tool names to include.

        Returns:
            List of tool objects.
        """
        # If LLM specified tool names, get those tools
        if tool_names:
            tools = []
            for name in tool_names:
                tool = self.tool_registry.get(name)
                if tool:
                    tools.append(tool)
                else:
                    logger.warning(f"Tool not found in registry: {name}")
            return tools

        # Otherwise, select tools intelligently based on task keywords
        # Extract keywords from current instruction (if state exists)
        if self.state and self.state.history:
            # Use most recent instruction for keyword extraction
            recent_instruction = self.state.history[-1].tuple.instruction
            keywords = context.extract_keywords_from_instruction(recent_instruction)
        else:
            keywords = []

        # Create selection criteria
        from aorchestra.tools import ToolSelectionCriteria

        criteria = ToolSelectionCriteria(
            keywords=keywords,
            max_tools=5,  # Limit number of tools for efficiency
        )

        # Select tools from registry
        selected = self.tool_registry.select_tools(criteria)

        logger.debug(
            f"Selected {len(selected)} tools for delegation: "
            f"{[t.name for t in selected]}"
        )

        return selected
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator_integration.py -v`
- [ ] Orchestrator initializes with ToolRegistry
- [ ] Orchestrator registers 4 built-in tools by default
- [ ] _filter_tools uses ToolRegistry for selection
- [ ] _build_context_for_subagent uses context curation
- [ ] Custom ToolRegistry can be injected via __init__

##### Manual Verification:

- [ ] Orchestrator initializes with empty tool_registry if None not passed
- [ ] ToolRegistry contains all 4 built-in tools after initialization
- [ ] Tool selection returns relevant tools based on keywords
- [ ] Context building includes relevant history items
- [ ] Existing tests still pass (no regressions)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to next phase.

---

### Phase 5: Testing and Validation

#### Overview

Write comprehensive tests for all new components and integration tests for the end-to-end workflow. Verify the system works correctly with real scenarios.

#### Changes Required:

##### 1. Create test file for ToolRegistry

**File**: `tests/test_tool_registry.py` (NEW)
**Changes**: Comprehensive tests for ToolRegistry

Key test classes:
- TestToolMetadata: Test Pydantic model
- TestToolRegistry: Test register, get, select, unregister operations

##### 2. Create test file for built-in tools

**File**: `tests/test_builtins.py` (NEW)
**Changes**: Comprehensive tests for all 4 built-in tools

Key test classes:
- TestCalculatorTool: Test arithmetic operations
- TestCodeExecuteTool: Test code execution, timeout, error handling
- TestWebSearchMockTool: Test search, keyword matching, custom index
- TestFileReadTool: Test file reading, path validation, encoding

##### 3. Create test file for context curation

**File**: `tests/test_context.py` (NEW)
**Changes**: Comprehensive tests for context curation

Key test classes:
- TestScoreRelevance: Test scoring algorithm
- TestExtractKeywordsFromInstruction: Test keyword extraction
- TestSelectRelevantHistory: Test history selection
- TestBuildContextForSubtask: Test context building

##### 4. Create integration test for Orchestrator

**File**: `tests/test_orchestrator_integration.py` (NEW)
**Changes**: End-to-end tests for ToolRegistry integration

Key test classes:
- TestOrchestratorToolRegistryIntegration: Test ToolRegistry integration
- TestOrchestratorContextCuration: Test context curation integration
- TestOrchestratorEndToEnd: Test complete workflow

#### Success Criteria:

##### Automated Verification:

- [ ] All new tests pass: `pytest tests/test_tool_registry.py tests/test_builtins.py tests/test_context.py tests/test_orchestrator_integration.py -v`
- [ ] All existing tests still pass: `pytest tests/ -v`
- [ ] Test coverage > 90% for new modules

##### Manual Verification:

- [ ] End-to-end workflow works correctly
- [ ] Tool selection appropriate for different subtask types
- [ ] Context curation improves relevance
- [ ] No regressions in existing functionality
- [ ] Documentation complete and accurate

**Note**: Complete all automated and manual verification before marking item complete.

---

## Testing Strategy

### Unit Tests:

#### ToolRegistry (`tests/test_tool_registry.py`):
- Test ToolMetadata model creation and validation
- Test tool registration (valid, duplicate, name mismatch, protocol violation)
- Test tool retrieval (get, get_metadata, get_all, list_tools)
- Test tool selection (by name, tags, capabilities, keywords)
- Test unregister operation
- Test edge cases (empty registry, missing tools, no matches)

#### Built-in Tools (`tests/test_builtins.py`):
- **CalculatorTool**: All operations (add, subtract, multiply, divide), error handling
- **CodeExecuteTool**: Simple execution, arithmetic, syntax errors, timeouts, stdout/stderr capture
- **WebSearchMockTool**: Python search, async search, no results, max_results limit, custom index
- **FileReadTool**: Read file, nonexistent file, path traversal prevention, custom allowed dirs, encoding handling

#### Context Curation (`tests/test_context.py`):
- **score_relevance**: No keywords, empty text, exact vs partial matches, case insensitivity, cumulative scoring
- **extract_keywords_from_instruction**: Empty input, stopwords filtering, technical terms, short word filtering
- **select_relevant_history**: Empty history, recent items, keyword scoring, max_items limit
- **build_context_for_subtask**: Empty inputs, action context, history inclusion, keyword filtering

### Integration Tests:

#### Orchestrator Integration (`tests/test_orchestrator_integration.py`):
- Test Orchestrator initialization with ToolRegistry
- Test built-in tools are registered automatically
- Test custom ToolRegistry injection
- Test _filter_tools with tool names
- Test _filter_tools without names (intelligent selection)
- Test _build_context_for_subagent with curation
- Test complete delegation workflow with tool selection
- Test context curation in real scenarios

### Manual Testing Steps:

1. **Tool Registry Manual Test**:
   ```python
   from aorchestra.tools import ToolRegistry, ToolMetadata
   from aorchestra.tools.builtins import CalculatorTool

   registry = ToolRegistry()
   calc = CalculatorTool()
   metadata = ToolMetadata(name="calculator", description="Calc", tags=["math"])

   registry.register(calc, metadata)
   assert "calculator" in registry
   assert registry.get("calculator") is calc
   ```

2. **Built-in Tools Manual Test**:
   ```python
   import asyncio
   from aorchestra.tools.builtins import CalculatorTool, CodeExecuteTool

   async def test():
       calc = CalculatorTool()
       result = await calc.execute(operation="add", a=5, b=3)
       assert result == 8

       code = CodeExecuteTool()
       result = await code.execute('print("Hello")')
       assert result["success"] is True

   asyncio.run(test())
   ```

3. **Orchestrator End-to-End Manual Test**:
   ```python
   from aorchestra.core.orchestrator import Orchestrator
   from aorchestra.models.config import ModelConfig

   model = ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1")
   orch = Orchestrator(model=model)

   # Verify tools are registered
   assert len(orch.tool_registry) >= 4
   assert "calculator" in orch.tool_registry

   # Test tool selection
   tools = orch._filter_tools(["calculator"])
   assert len(tools) == 1
   assert tools[0].name == "calculator"
   ```

## Migration Notes

### Breaking Changes:
- **Orchestrator.__init__** signature change: Added optional `tool_registry` parameter
  - **Migration**: Existing code will continue to work (None default creates default registry)
  - **Recommended**: Pass custom ToolRegistry if needed

### Backward Compatibility:
- All existing tests should pass without modification
- Tool protocol unchanged from items 001-002
- SubAgent tool invocation unchanged
- Existing tools (EchoTool, CalculatorTool, ErrorTool) still work

### Deprecations:
- None

### Data Migration:
- No data to migrate (no persistent state)

## References

- Research: `C:\Users\strau\clawd\aorchestra\.wreckit\items\003-dynamic-context-tool-selection\research.md`
- Item Definition: `C:\Users\strau\clawd\aorchestra\.wreckit\items\003-dynamic-context-tool-selection\item.json`
- Tool Protocol: `aorchestra/tools/base.py:12-41`
- Tool Validation: `aorchestra/tools/base.py:44-61`
- Existing Mock Tools: `aorchestra/tools/mock.py:1-76`
- Orchestrator Placeholder: `aorchestra/core/orchestrator.py:293-312`
- Orchestrator Context Building: `aorchestra/core/orchestrator.py:263-286`
- SubAgent Tool Handling: `aorchestra/core/agents.py:97-226`
- DelegateAction Model: `aorchestra/orchestrator/actions.py:12-31`
- Existing Tool Tests: `tests/test_tools.py:1-128`
- Existing Orchestrator Tests: `tests/test_orchestrator.py:1-163`
