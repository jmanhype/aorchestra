# Core 4-tuple agent abstraction Implementation Plan

## Implementation Plan Title

Foundational 4-Tuple Agent Abstraction for Dynamic Sub-Agent Creation

## Overview

Implement the core AgentTuple dataclass representing the 4-tuple abstraction Φ = (Instruction, Context, Tools, Model), along with the AgentFactory for instantiating executable SubAgent instances and the SubAgent base class with async execute() functionality. This greenfield implementation establishes the foundational agent abstraction that all other AOrchestra components (items 002-005) depend on, enabling dynamic creation of specialized sub-agents that run in isolation with their assigned context and tools.

## Current State

**Greenfield Implementation - No existing code**

The project currently contains only documentation and configuration files:
- **README.md** establishes the core concept but no implementation exists
- No Python package structure (no `aorchestra/` directory)
- No dependencies configured (no pyproject.toml, requirements.txt, or setup.py)
- No test infrastructure (no tests/ directory or pytest configuration)
- Items 002-005 explicitly depend on this component but cannot start until it's complete

**Key Constraints:**
- Must use Python 3.12+ with Pydantic for data models
- Must support async operations via OpenAI-compatible API client
- Must work with Z.ai GLM-4.7 models (OpenAI-compatible endpoint)
- Tools must follow consistent interface (name, description, execute) for item 003 compatibility
- Model configuration must be extensible for item 004's ModelRegistry

**Dependencies Downstream:**
- Item 002 (Orchestrator): Requires AgentTuple and SubAgent for Delegate(Φ) operations
- Item 003 (ToolRegistry): Requires tool interface consistency
- Item 004 (ModelRouting): Requires ModelConfig structure for tier registry
- Item 005 (Evaluation): Depends on all prior components

## Desired End State

A fully functional, tested Python package providing the 4-tuple agent abstraction with the following deliverables:

### Package Structure
```
aorchestra/
├── __init__.py                 # Package initialization, version 0.1.0
├── core/
│   ├── __init__.py            # Exports AgentTuple, SubAgent, AgentFactory, Observation
│   ├── tuples.py              # AgentTuple dataclass with 4 fields
│   ├── agents.py              # SubAgent base class with async execute()
│   ├── factory.py             # AgentFactory.create(tuple) implementation
│   └── observations.py        # Observation, ObservationResult, Artifact models
├── tools/
│   ├── __init__.py            # Exports Tool, Tool base classes
│   └── base.py                # Tool protocol/base class
└── models/
    ├── __init__.py            # Exports ModelConfig
    └── config.py              # ModelConfig dataclass
tests/
├── __init__.py
├── conftest.py                # Pytest fixtures for mocking
├── test_tuples.py             # AgentTuple validation tests
├── test_agents.py             # SubAgent execution tests
├── test_factory.py            # AgentFactory tests
└── test_observations.py       # Observation serialization tests
pyproject.toml                 # Project metadata and dependencies
pytest.ini                     # Test configuration with async support
requirements.txt               # Pinned dependencies
examples/
└── basic_agent.py             # Example usage demonstrating end-to-end flow
```

### Functional Requirements

1. **AgentTuple Dataclass** (core/tuples.py):
   - Fields: instruction (str), context (str), tools (list[Tool]), model (ModelConfig)
   - Pydantic validation with descriptive error messages
   - JSON serialization/deserialization for state persistence
   - Type hints for IDE support

2. **Observation Models** (core/observations.py):
   - result_summary (str): Human-readable summary of agent execution
   - artifacts (dict[str, Any]): Structured outputs (files, data, intermediate results)
   - error_logs (list[str]): Captured errors/warnings during execution
   - Optional metadata field for extensibility

3. **Tool Interface** (tools/base.py):
   - Protocol/base class with name (str), description (str)
   - Async execute(**kwargs) method returning Any
   - Mock tools for testing (EchoTool, ErrorTool, CalculatorTool)

4. **Model Configuration** (models/config.py):
   - ModelConfig with name (str), api_base (str), api_key (str)
   - Optional parameters: temperature (float), max_tokens (int)
   - Support for Z.ai GLM models with custom base_url
   - Validation for required fields

5. **SubAgent Base Class** (core/agents.py):
   - Async execute() method accepting AgentTuple
   - Builds prompt from instruction + context
   - Invokes OpenAI-compatible API with provided tools
   - Returns Observation with result_summary, artifacts, error_logs
   - Isolation: accesses only assigned context/tools, no shared state
   - Error handling: captures exceptions in error_logs, returns partial results

6. **AgentFactory** (core/factory.py):
   - create(tuple: AgentTuple) -> SubAgent instance method
   - Validation: ensures tools are callable, model config valid
   - Support for concurrent agent creation (async-friendly)
   - Clear error messages for invalid configurations

7. **LLM Integration**:
   - OpenAI SDK (v1.0+) with custom base_url for Z.ai
   - Async client for non-blocking operations
   - Tool calling support (native if GLM-4.7 supports, fallback to prompt-based)
   - Mock client for testing (no API calls in unit tests)

### Verification Criteria

**Automated Tests:**
- All unit tests pass: `pytest tests/ -v`
- Type checking passes: `mypy aorchestra/` (if mypy configured)
- Test coverage ≥80%: `pytest --cov=aorchestra`
- No pydantic validation errors in test cases
- Async tests execute without blocking

**Manual Verification:**
- Example script runs successfully: `python examples/basic_agent.py`
- AgentTuple serializes to/from JSON correctly
- SubAgent.execute() returns proper Observation structure
- Z.ai API integration works (with valid credentials)
- Tool execution produces expected results
- Error handling captures failures in error_logs

### Key Discoveries:

- **README.md:5-7** defines the 4-tuple structure Φ = (Instruction, Context, Tools, Model) which must be implemented exactly as specified
- **.wreckit/items/003/item.json** requires tools with "name, description, execute" interface - must design Tool protocol to accommodate this
- **.wreckit/items/004/item.json** references ModelRegistry with tiers - ModelConfig must be simple enough for ModelRegistry wrapper later
- **No existing test infrastructure** - must create pytest.ini, conftest.py with fixtures, and establish testing patterns from scratch
- **Z.ai OpenAI-compatible API** - verify GLM-4.7 supports tool calling; implement manual tool invocation as fallback if needed
- **Greenfield advantage** - can establish clean patterns without legacy constraints, but must ensure compatibility with downstream items 002-005

## What We're NOT Doing

**Out of Scope for Item 001:**

1. **Orchestrator Implementation** (Item 002):
   - No Delegate/Finish actions
   - No state history management
   - No multi-step orchestration logic
   - No decision loops

2. **ToolRegistry** (Item 003):
   - Only base Tool interface, no registry implementation
   - No tool selection logic
   - No built-in tools beyond mock/test tools (calculator, web_search_mock will be in item 003)
   - No tool metadata management

3. **ModelRegistry** (Item 004):
   - Only ModelConfig dataclass, no registry implementation
   - No cost tracking
   - No model tier selection logic
   - No complexity heuristics

4. **Evaluation Harness** (Item 005):
   - No benchmark integration
   - No task definitions
   - No performance metrics

5. **Advanced Features:**
   - No streaming responses (sync execute only, streaming can be added later)
   - No multi-modal support (text-only for now)
   - No prompt template system (simple concatenation in item 001)
   - No context curation (full context passed to sub-agents)
   - No state persistence beyond Observation serialization
   - No retry logic or fault tolerance beyond basic error capture

6. **Production Hardening:**
   - No authentication/authorization
   - No rate limiting
   - No caching
   - No monitoring/observability beyond structured logs

**Boundaries:**
- Item 001 provides the *primitive* (4-tuple abstraction) that higher-level items compose
- Focus on correctness, testability, and clear interfaces over optimization
- Keep abstractions simple and extensible - items 002-005 will add complexity

## Implementation Approach

**Test-Driven Development (TDD) with Incremental Phases**

Since this is a foundational greenfield component with 4 downstream dependencies, implement incrementally with comprehensive testing at each phase. Each phase is independently testable and verifiable before proceeding to the next.

**Key Architectural Decisions:**

1. **Pydantic v2 for All Data Models**:
   - AgentTuple as `pydantic.dataclasses.dataclass` ( cleaner than BaseModel for data containers)
   - Observation as `pydantic.BaseModel` (better for result structures)
   - Enables automatic validation, JSON serialization, type checking
   - Version pinned to ≥2.0 in pyproject.toml

2. **Async-First Design**:
   - All LLM calls use `async/await` with OpenAI SDK's async client
   - SubAgent.execute() is async by design
   - AgentFactory supports concurrent agent creation
   - Tests use `pytest-asyncio` with `asyncio_mode = auto`

3. **Tool Protocol (not Base Class)**:
   - Use `typing.Protocol` for Tool interface (duck typing, more flexible)
   - Allows functions, classes, or any callable with matching signature
   - Accommodates item 003's diverse tool types
   - Mock tools implement protocol for testing

4. **OpenAI SDK with Custom Base URL**:
   - Use official `openai` >= 1.0 SDK (not langchain-openai)
   - Set `api_base` parameter for Z.ai endpoint
   - Native tool calling if GLM-4.7 supports it, manual fallback otherwise
   - Mock client for testing (via monkeypatch/fixtures)

5. **Simple Prompt Construction**:
   - Template: `f"{instruction}\n\nContext:\n{context}"`
   - No templating engine (item 003 can add Jinja2 if needed)
   - Flexible for future enhancements

6. **Observation Structure**:
   - All fields optional except result_summary
   - Artifacts as dict for maximum flexibility
   - Error logs as list for chronological tracking
   - Extensible via optional metadata field

**Dependency Management:**

```toml
[tool.poetry.dependencies]
python = "^3.12"
pydantic = "^2.0"
openai = "^1.0"

[tool.poetry.dev-dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
pytest-mock = "^3.12"
```

**Implementation Order:**
1. **Phase 1**: Data models (no dependencies, establishes core types)
2. **Phase 2**: Tool/Model abstractions (foundation for execution)
3. **Phase 3**: SubAgent (core logic, depends on 1-2)
4. **Phase 4**: AgentFactory (simple wrapper, depends on 1-3)
5. **Phase 5**: Z.ai integration (can be mocked in earlier phases)

**Testing Strategy:**
- Unit tests for each module (≥80% coverage)
- Mock all external dependencies (OpenAI client, file I/O)
- Integration tests with example script
- Manual testing with real Z.ai API (optional, requires credentials)

**Rollback Strategy:**
- Each phase is independently testable
- Git commit after each completed phase
- Clear success criteria before proceeding
- Can revert to any phase checkpoint if issues arise

---

## Phases

### Phase 1: Core Data Models

#### Overview

Establish the foundational data structures for the 4-tuple agent abstraction: AgentTuple (the core 4-tuple), Observation (execution results), and ModelConfig (LLM configuration). This phase has no dependencies and creates the type system foundation for all subsequent phases.

#### Changes Required:

##### 1. Project Setup

**File**: `pyproject.toml` (NEW)
**Changes**: Create project metadata and dependency specification

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "aorchestra"
version = "0.1.0"
description = "AOrchestra: Open Implementation of Agentic Orchestration"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0,<3.0",
    "openai>=1.0,<2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "mypy>=1.8",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.coverage.run]
source = ["aorchestra"]
```

**File**: `pytest.ini` (NEW)
**Changes**: Pytest configuration for async support

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=aorchestra --cov-report=html
```

**File**: `requirements.txt` (NEW)
**Changes**: Pinned dependencies for reproducibility

```
pydantic==2.7.4
openai==1.54.0
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
pytest-mock==3.14.0
```

##### 2. Package Structure

**File**: `aorchestra/__init__.py` (NEW)
**Changes**: Package initialization with version and exports

```python
"""AOrchestra: Open Implementation of Agentic Orchestration.

Any agent is a dynamically instantiable 4-tuple:
    Φ = (Instruction, Context, Tools, Model)
"""

__version__ = "0.1.0"

from aorchestra.core import AgentTuple, SubAgent, AgentFactory, Observation

__all__ = [
    "__version__",
    "AgentTuple",
    "SubAgent",
    "AgentFactory",
    "Observation",
]
```

##### 3. Observation Models

**File**: `aorchestra/core/observations.py` (NEW)
**Changes**: Define Observation result structure

```python
"""Observation models for sub-agent execution results."""

from typing import Any
from pydantic import BaseModel, Field


class Observation(BaseModel):
    """Result of a SubAgent execution.

    Captures the outcome of executing a 4-tuple agent, including
    the result summary, any artifacts produced, and error logs.
    """

    result_summary: str = Field(
        ...,
        description="Human-readable summary of the agent's execution result",
    )
    artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured outputs produced during execution "
        "(files, data, intermediate results)",
    )
    error_logs: list[str] = Field(
        default_factory=list,
        description="Errors or warnings encountered during execution",
    )

    def add_error(self, error: str) -> None:
        """Add an error message to the error logs."""
        self.error_logs.append(error)

    def add_artifact(self, key: str, value: Any) -> None:
        """Add an artifact to the artifacts dictionary."""
        self.artifacts[key] = value
```

**File**: `tests/test_observations.py` (NEW)
**Changes**: Unit tests for Observation model

```python
"""Tests for Observation models."""

import pytest
from aorchestra.core.observations import Observation


class TestObservation:
    """Test Observation model validation and behavior."""

    def test_create_observation_with_summary_only(self):
        """Observation can be created with just a result_summary."""
        obs = Observation(result_summary="Task completed successfully")
        assert obs.result_summary == "Task completed successfully"
        assert obs.artifacts == {}
        assert obs.error_logs == []

    def test_observation_with_artifacts(self):
        """Observation can store structured artifacts."""
        obs = Observation(
            result_summary="Generated code",
            artifacts={"code": "print('hello')", "language": "python"},
        )
        assert obs.artifacts["code"] == "print('hello')"
        assert obs.artifacts["language"] == "python"

    def test_observation_with_errors(self):
        """Observation can capture error logs."""
        obs = Observation(
            result_summary="Partial completion",
            error_logs=["Warning: timeout", "Error: API rate limit"],
        )
        assert len(obs.error_logs) == 2
        assert "timeout" in obs.error_logs[0]

    def test_add_error_method(self):
        """Observation.add_error() appends to error_logs."""
        obs = Observation(result_summary="Test")
        obs.add_error("New error")
        assert len(obs.error_logs) == 1
        assert obs.error_logs[0] == "New error"

    def test_add_artifact_method(self):
        """Observation.add_artifact() adds to artifacts dict."""
        obs = Observation(result_summary="Test")
        obs.add_artifact("output", "result")
        assert obs.artifacts["output"] == "result"

    def test_observation_serialization(self):
        """Observation can serialize to/from JSON."""
        obs = Observation(
            result_summary="Test",
            artifacts={"key": "value"},
            error_logs=["error1"],
        )
        json_str = obs.model_dump_json()
        restored = Observation.model_validate_json(json_str)
        assert restored.result_summary == obs.result_summary
        assert restored.artifacts == obs.artifacts
        assert restored.error_logs == obs.error_logs
```

##### 4. Model Configuration

**File**: `aorchestra/models/config.py` (NEW)
**Changes**: Define ModelConfig for LLM settings

```python
"""Model configuration for LLM backends."""

from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for an LLM model.

    Designed to work with OpenAI-compatible APIs (Z.ai, GLM-4.7).
    Simple structure that can be extended by ModelRegistry in item 004.
    """

    name: str = Field(
        ...,
        description="Model name (e.g., 'glm-4.7', 'glm-4-flash')",
    )
    api_base: str = Field(
        ...,
        description="Base URL for the API endpoint",
    )
    api_key: str = Field(
        default="",
        description="API key for authentication (empty for local models)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = creative)",
    )
    max_tokens: int = Field(
        default=2048,
        gt=0,
        description="Maximum tokens in the response",
    )

    @field_validator("api_base")
    @classmethod
    def api_base_must_be_valid_url(cls, v: str) -> str:
        """Ensure api_base is a valid URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("api_base must start with http:// or https://")
        return v

    def to_openai_kwargs(self) -> dict:
        """Convert to kwargs suitable for OpenAI client initialization."""
        return {
            "api_key": self.api_key or "dummy",  # OpenAI requires non-empty
            "base_url": self.api_base,
        }
```

**File**: `tests/test_models.py` (NEW)
**Changes**: Unit tests for ModelConfig

```python
"""Tests for ModelConfig."""

import pytest
from pydantic import ValidationError
from aorchestra.models.config import ModelConfig


class TestModelConfig:
    """Test ModelConfig validation."""

    def test_create_model_config_minimal(self):
        """ModelConfig with required fields only."""
        config = ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )
        assert config.name == "glm-4.7"
        assert config.api_base == "https://api.z.ai/v1"
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2048  # default

    def test_create_model_config_with_all_fields(self):
        """ModelConfig with all fields specified."""
        config = ModelConfig(
            name="glm-4-flash",
            api_base="https://api.z.ai/v1",
            api_key="sk-test",
            temperature=0.5,
            max_tokens=1024,
        )
        assert config.temperature == 0.5
        assert config.max_tokens == 1024

    def test_invalid_api_base_raises_error(self):
        """api_base must start with http:// or https://."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="invalid-url")

    def test_temperature_out_of_range_raises_error(self):
        """temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1", temperature=3.0)

    def test_max_tokens_must_be_positive(self):
        """max_tokens must be > 0."""
        with pytest.raises(ValidationError):
            ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1", max_tokens=0)

    def test_to_openai_kwargs(self):
        """to_openai_kwargs() returns correct dictionary."""
        config = ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
            api_key="sk-test",
        )
        kwargs = config.to_openai_kwargs()
        assert kwargs["base_url"] == "https://api.z.ai/v1"
        assert kwargs["api_key"] == "sk-test"
```

##### 5. AgentTuple Dataclass

**File**: `aorchestra/core/tuples.py` (NEW)
**Changes**: Define AgentTuple 4-tuple dataclass

```python
"""Core 4-tuple agent abstraction: Φ = (Instruction, Context, Tools, Model)."""

from typing import Any
from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from aorchestra.models.config import ModelConfig


@dataclass
class AgentTuple:
    """A 4-tuple defining an agent: Φ = (Instruction, Context, Tools, Model).

    This is the foundational abstraction for all agents in AOrchestra.
    An orchestrator creates AgentTuples dynamically and uses AgentFactory
    to instantiate executable SubAgent instances.
    """

    instruction: str = Field(
        ...,
        description="The task instruction for the agent",
    )
    context: str = Field(
        default="",
        description="Relevant context information (previous observations, data, etc.)",
    )
    tools: list[Any] = Field(
        default_factory=list,
        description="List of tools available to the agent",
    )
    model: ModelConfig = Field(
        ...,
        description="Model configuration for LLM backend",
    )

    @field_validator("instruction")
    @classmethod
    def instruction_must_not_be_empty(cls, v: str) -> str:
        """Instruction must not be empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError("instruction must not be empty")
        return v.strip()

    def build_prompt(self) -> str:
        """Build a prompt from instruction and context.

        Simple concatenation for item 001. Can be enhanced with
        templating in item 003.
        """
        if self.context:
            return f"{self.instruction}\n\nContext:\n{self.context}"
        return self.instruction
```

**File**: `tests/test_tuples.py` (NEW)
**Changes**: Unit tests for AgentTuple

```python
"""Tests for AgentTuple."""

import pytest
from pydantic import ValidationError
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig


class TestAgentTuple:
    """Test AgentTuple validation and behavior."""

    @pytest.fixture
    def model_config(self):
        """Default model config for tests."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    def test_create_agent_tuple_minimal(self, model_config):
        """AgentTuple with instruction and model only."""
        tuple_def = AgentTuple(
            instruction="Solve this task",
            model=model_config,
        )
        assert tuple_def.instruction == "Solve this task"
        assert tuple_def.context == ""
        assert tuple_def.tools == []
        assert tuple_def.model == model_config

    def test_create_agent_tuple_full(self, model_config):
        """AgentTuple with all fields specified."""
        tuple_def = AgentTuple(
            instruction="Calculate sum",
            context="Numbers: 1, 2, 3",
            tools=["calculator"],
            model=model_config,
        )
        assert tuple_def.context == "Numbers: 1, 2, 3"
        assert tuple_def.tools == ["calculator"]

    def test_empty_instruction_raises_error(self, model_config):
        """instruction must not be empty."""
        with pytest.raises(ValidationError) as exc:
            AgentTuple(instruction="", model=model_config)
        assert "instruction must not be empty" in str(exc.value)

    def test_whitespace_instruction_is_trimmed(self, model_config):
        """Leading/trailing whitespace in instruction is trimmed."""
        tuple_def = AgentTuple(
            instruction="  Solve task  ",
            model=model_config,
        )
        assert tuple_def.instruction == "Solve task"

    def test_build_prompt_without_context(self, model_config):
        """build_prompt() returns just instruction when no context."""
        tuple_def = AgentTuple(
            instruction="Task description",
            model=model_config,
        )
        assert tuple_def.build_prompt() == "Task description"

    def test_build_prompt_with_context(self, model_config):
        """build_prompt() combines instruction and context."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            context="Numbers: 1, 2, 3",
            model=model_config,
        )
        prompt = tuple_def.build_prompt()
        assert "Calculate" in prompt
        assert "Numbers: 1, 2, 3" in prompt

    def test_serialization(self, model_config):
        """AgentTuple can be serialized to/from JSON."""
        tuple_def = AgentTuple(
            instruction="Task",
            context="Context",
            tools=["tool1"],
            model=model_config,
        )
        # Pydantic dataclasses support model_dump_json()
        import json
        from pydantic import TypeAdapter

        adapter = TypeAdapter(AgentTuple)
        json_str = adapter.dump_json(tuple_def)
        restored = adapter.validate_json(json_str)
        assert restored.instruction == tuple_def.instruction
        assert restored.context == tuple_def.context
```

##### 6. Module Initialization

**File**: `aorchestra/models/__init__.py` (NEW)
**Changes**: Export ModelConfig

```python
"""Model configuration module."""

from aorchestra.models.config import ModelConfig

__all__ = ["ModelConfig"]
```

**File**: `aorchestra/core/__init__.py` (NEW)
**Changes**: Export core types (partial, will add SubAgent, AgentFactory in later phases)

```python
"""Core agent abstraction module."""

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation

__all__ = [
    "AgentTuple",
    "Observation",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass: `pytest tests/test_observations.py tests/test_models.py tests/test_tuples.py -v`
- [ ] Test coverage ≥90% for new modules: `pytest --cov=aorchestra.core --cov=aorchestra.models`
- [ ] No type errors (if using mypy): `mypy aorchestra/`
- [ ] Package installs correctly: `pip install -e .`
- [ ] Imports work: `python -c "from aorchestra import AgentTuple, Observation, ModelConfig"`

##### Manual Verification:

- [ ] Review Observation model - fields match requirements (result_summary, artifacts, error_logs)
- [ ] Review ModelConfig - compatible with Z.ai API format
- [ ] Review AgentTuple - all 4 fields present, validation working
- [ ] Verify JSON serialization works for state persistence (item 002 dependency)
- [ ] Confirm tool interface placeholder is flexible for item 003

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 2.

---

### Phase 2: Tool and Model Abstractions

#### Overview

Define the Tool protocol/interface that establishes the contract for all tools in AOrchestra. This interface must accommodate item 003's requirements (name, description, execute) while remaining flexible for diverse tool implementations. Also implement mock tools for testing the SubAgent in Phase 3.

#### Changes Required:

##### 1. Tool Protocol Definition

**File**: `aorchestra/tools/base.py` (NEW)
**Changes**: Define Tool protocol for tool interface

```python
"""Tool interface and base classes.

Tools are callable objects that sub-agents can use to perform actions.
Item 003 will implement ToolRegistry with built-in tools.
This module defines the interface that all tools must follow.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Protocol defining the tool interface.

    A tool must have a name, description, and be callable.
    Uses Protocol (duck typing) for maximum flexibility - any object
    with matching signature qualifies as a tool.

    Compatible with item 003's requirement for tools with
    "name, description, execute" interface.
    """

    name: str
    """Human-readable name of the tool."""

    description: str
    """Description of what the tool does and how to use it."""

    async def execute(**kwargs: Any) -> Any:
        """Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments.

        Returns:
            Any: The result of tool execution.

        Raises:
            Exception: Tool-specific errors (captured in Observation.error_logs).
        """
        ...


def validate_tool(tool: Any) -> Tool:
    """Validate that an object implements the Tool protocol.

    Args:
        tool: Object to validate.

    Returns:
        Tool: The validated tool.

    Raises:
        TypeError: If the object doesn't implement Tool protocol.
    """
    if not isinstance(tool, Tool):
        raise TypeError(
            f"Object {tool!r} does not implement Tool protocol. "
            f"Tools must have 'name', 'description', and async 'execute' method."
        )
    return tool
```

##### 2. Mock Tools for Testing

**File**: `aorchestra/tools/mock.py` (NEW)
**Changes**: Implement mock tools for testing

```python
"""Mock tools for testing SubAgent execution."""

from typing import Any
from aorchestra.tools.base import Tool


class EchoTool:
    """A simple tool that echoes back its input.

    Useful for testing tool invocation without side effects.
    """

    name: str = "echo"
    description: str = "Echoes back the input message"

    async def execute(self, message: str) -> str:
        """Echo the input message.

        Args:
            message: The message to echo.

        Returns:
            The same message.
        """
        return f"Echo: {message}"


class CalculatorTool:
    """A basic calculator tool for arithmetic operations."""

    name: str = "calculator"
    description: str = "Performs basic arithmetic: add, subtract, multiply, divide"

    async def execute(self, operation: str, a: float, b: float) -> float:
        """Execute a calculator operation.

        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide'
            a: First operand
            b: Second operand

        Returns:
            Result of the calculation

        Raises:
            ValueError: If operation is unknown or dividing by zero
        """
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


class ErrorTool:
    """A tool that always raises an error.

    Useful for testing error handling in SubAgent.
    """

    name: str = "error_tool"
    description: str = "Always raises a test error"

    async def execute(self, message: str = "Test error") -> None:
        """Raise a test error.

        Args:
            message: Error message

        Raises:
            RuntimeError: Always raises this error
        """
        raise RuntimeError(f"Intentional test error: {message}")
```

##### 3. Tool Tests

**File**: `tests/test_tools.py` (NEW)
**Changes**: Unit tests for tool protocol and mock tools

```python
"""Tests for tool protocol and mock tools."""

import pytest
from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.mock import EchoTool, CalculatorTool, ErrorTool


class TestToolProtocol:
    """Test Tool protocol validation."""

    def test_valid_tool_passes_validation(self):
        """A valid tool implements the Tool protocol."""
        echo = EchoTool()
        assert validate_tool(echo) == echo

    def test_invalid_object_raises_type_error(self):
        """An object without Tool interface raises TypeError."""
        invalid = {"name": "bad"}  # Dict doesn't implement Tool
        with pytest.raises(TypeError) as exc:
            validate_tool(invalid)
        assert "does not implement Tool protocol" in str(exc.value)

    def test_tool_with_missing_name_raises_error(self):
        """Tool without 'name' attribute fails validation."""
        class BadTool:
            description = "Missing name"
            async def execute(self):
                pass

        with pytest.raises(TypeError):
            validate_tool(BadTool())


class TestEchoTool:
    """Test EchoTool functionality."""

    @pytest.mark.asyncio
    async def test_echo_tool_returns_message(self):
        """EchoTool echoes back the input message."""
        tool = EchoTool()
        result = await tool.execute(message="Hello, world!")
        assert result == "Echo: Hello, world!"

    def test_echo_tool_has_name_and_description(self):
        """EchoTool has required name and description."""
        tool = EchoTool()
        assert tool.name == "echo"
        assert tool.description != ""


class TestCalculatorTool:
    """Test CalculatorTool functionality."""

    @pytest.mark.asyncio
    async def test_calculator_add(self):
        """Calculator can add two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="add", a=5, b=3)
        assert result == 8

    @pytest.mark.asyncio
    async def test_calculator_multiply(self):
        """Calculator can multiply two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="multiply", a=4, b=7)
        assert result == 28

    @pytest.mark.asyncio
    async def test_calculator_divide(self):
        """Calculator can divide two numbers."""
        tool = CalculatorTool()
        result = await tool.execute(operation="divide", a=10, b=2)
        assert result == 5

    @pytest.mark.asyncio
    async def test_calculator_divide_by_zero_raises_error(self):
        """Calculator raises error for division by zero."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            await tool.execute(operation="divide", a=5, b=0)

    @pytest.mark.asyncio
    async def test_calculator_unknown_operation_raises_error(self):
        """Calculator raises error for unknown operations."""
        tool = CalculatorTool()
        with pytest.raises(ValueError, match="Unknown operation"):
            await tool.execute(operation="modulo", a=10, b=3)


class TestErrorTool:
    """Test ErrorTool functionality."""

    @pytest.mark.asyncio
    async def test_error_tool_always_raises(self):
        """ErrorTool always raises a RuntimeError."""
        tool = ErrorTool()
        with pytest.raises(RuntimeError, match="Intentional test error"):
            await tool.execute(message="Test")
```

##### 4. Module Initialization

**File**: `aorchestra/tools/__init__.py` (NEW)
**Changes**: Export tool types

```python
"""Tools module for AOrchestra."""

from aorchestra.tools.base import Tool, validate_tool
from aorchestra.tools.mock import EchoTool, CalculatorTool, ErrorTool

__all__ = [
    "Tool",
    "validate_tool",
    "EchoTool",
    "CalculatorTool",
    "ErrorTool",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass: `pytest tests/test_tools.py -v`
- [ ] Test coverage ≥90% for tools module
- [ ] Tool protocol correctly validates valid tools: `python -c "from aorchestra.tools import EchoTool, validate_tool; validate_tool(EchoTool())"`
- [ ] Tool protocol correctly rejects invalid tools: test with dict, function without signature, etc.
- [ ] Mock tools execute correctly in async context

##### Manual Verification:

- [ ] Review Tool protocol - compatible with item 003 requirements (name, description, execute)
- [ ] Verify validate_tool provides clear error messages
- [ ] Test mock tools manually in Python REPL
- [ ] Confirm tools can be stored in AgentTuple.tools list
- [ ] Verify tools work with AgentTuple serialization (tools excluded from JSON, which is expected)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 3.

---

### Phase 3: SubAgent Base Class

#### Overview

Implement the SubAgent base class with async execute() method. This is the core execution engine that takes an AgentTuple, builds a prompt, calls the LLM with available tools, and returns a structured Observation. This phase integrates all components from Phases 1-2 and adds the OpenAI client for LLM communication.

#### Changes Required:

##### 1. SubAgent Implementation

**File**: `aorchestra/core/agents.py` (NEW)
**Changes**: Implement SubAgent base class with async execute()

```python
"""SubAgent execution engine.

SubAgent takes an AgentTuple and executes it by:
1. Building a prompt from instruction + context
2. Calling the LLM with available tools
3. Returning a structured Observation

Each sub-agent runs in isolation with only its assigned context and tools.
"""

import asyncio
import logging
from typing import Any
from openai import AsyncOpenAI

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.tools.base import Tool

logger = logging.getLogger(__name__)


class SubAgent:
    """A sub-agent that executes a single 4-tuple.

    SubAgents are created by AgentFactory and run in isolation.
    They have access only to their assigned context and tools.
    """

    def __init__(self, tuple_def: AgentTuple):
        """Initialize the SubAgent with an AgentTuple.

        Args:
            tuple_def: The 4-tuple defining this agent's configuration.
        """
        self.tuple = tuple_def
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialized OpenAI client."""
        if self._client is None:
            kwargs = self.tuple.model.to_openai_kwargs()
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def execute(self) -> Observation:
        """Execute the sub-agent's task.

        Builds a prompt from instruction + context, calls the LLM,
        invokes tools if needed, and returns a structured Observation.

        Returns:
            Observation with result_summary, artifacts, and error_logs.
        """
        try:
            return await self._execute_impl()
        except Exception as e:
            logger.exception("SubAgent execution failed")
            return Observation(
                result_summary=f"Execution failed: {e}",
                error_logs=[f"Critical error: {type(e).__name__}: {e}"],
            )

    async def _execute_impl(self) -> Observation:
        """Internal implementation of execute().

        Returns:
            Observation with execution results.
        """
        # Build prompt from instruction + context
        prompt = self.tuple.build_prompt()
        logger.info(f"Executing sub-agent with prompt: {prompt[:100]}...")

        # Prepare tools for OpenAI function calling (if supported)
        tools = self._prepare_tools()
        artifacts: dict[str, Any] = {}
        error_logs: list[str] = []

        # Call LLM
        response = await self._call_llm(prompt, tools)

        # Process response and invoke tools if needed
        result_summary, tool_artifacts, tool_errors = await self._process_response(
            response, tools
        )
        artifacts.update(tool_artifacts)
        error_logs.extend(tool_errors)

        return Observation(
            result_summary=result_summary,
            artifacts=artifacts,
            error_logs=error_logs,
        )

    def _prepare_tools(self) -> list[dict[str, Any]]:
        """Convert tool objects to OpenAI function-calling format.

        Returns:
            List of tool definitions in OpenAI format.
        """
        openai_tools = []
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and hasattr(tool, "description"):
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": {},  # Could be enhanced with schema
                        },
                    },
                })
        return openai_tools

    async def _call_llm(
        self, prompt: str, tools: list[dict[str, Any]]
    ) -> Any:
        """Call the LLM with the prompt and tools.

        Args:
            prompt: The prompt to send to the LLM.
            tools: List of tools in OpenAI format.

        Returns:
            LLM response object.
        """
        kwargs = {
            "model": self.tuple.model.name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.tuple.model.temperature,
            "max_tokens": self.tuple.model.max_tokens,
        }

        # Add tools if available (may not be supported by all models)
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)
        return response

    async def _process_response(
        self, response: Any, tool_definitions: list[dict[str, Any]]
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Process the LLM response and invoke tools if requested.

        Args:
            response: Raw LLM response.
            tool_definitions: List of tool definitions.

        Returns:
            Tuple of (result_summary, artifacts, error_logs).
        """
        choice = response.choices[0]
        message = choice.message

        # Check if model requested tool calls
        tool_calls = getattr(message, "tool_calls", None)

        if tool_calls:
            return await self._handle_tool_calls(tool_calls)
        else:
            # Simple text response
            return message.content, {}, []

    async def _handle_tool_calls(
        self, tool_calls: list[Any]
    ) -> tuple[str, dict[str, Any], list[str]]:
        """Handle tool calls requested by the LLM.

        Args:
            tool_calls: List of tool call objects from LLM.

        Returns:
            Tuple of (result_summary, artifacts, error_logs).
        """
        artifacts = {}
        error_logs = []
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool = self._find_tool(tool_name)

            if tool is None:
                error_logs.append(f"Tool not found: {tool_name}")
                continue

            try:
                # Parse arguments (JSON string -> dict)
                import json
                args = json.loads(tool_call.function.arguments)

                # Execute tool
                result = await tool.execute(**args)
                results.append(f"{tool_name}: {result}")
                artifacts[tool_name] = result

            except Exception as e:
                error_msg = f"Tool {tool_name} failed: {e}"
                error_logs.append(error_msg)
                logger.exception(error_msg)

        # Generate summary from tool results
        if results:
            result_summary = "Executed tools: " + ", ".join(results)
        else:
            result_summary = "Tool execution completed with errors"

        return result_summary, artifacts, error_logs

    def _find_tool(self, name: str) -> Tool | None:
        """Find a tool by name in the tuple's tool list.

        Args:
            name: Tool name to find.

        Returns:
            Tool object or None if not found.
        """
        for tool in self.tuple.tools:
            if hasattr(tool, "name") and tool.name == name:
                return tool
        return None
```

##### 2. SubAgent Tests

**File**: `tests/test_agents.py` (NEW)
**Changes**: Unit tests for SubAgent

```python
"""Tests for SubAgent execution."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.agents import SubAgent
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool


class TestSubAgent:
    """Test SubAgent execution logic."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def simple_tuple(self, model_config):
        """Simple tuple without tools."""
        return AgentTuple(
            instruction="Say hello",
            model=model_config,
        )

    @pytest.fixture
    def tuple_with_tools(self, model_config):
        """Tuple with echo and calculator tools."""
        return AgentTuple(
            instruction="Use tools",
            tools=[EchoTool(), CalculatorTool()],
            model=model_config,
        )

    def test_subagent_initialization(self, simple_tuple):
        """SubAgent initializes with AgentTuple."""
        agent = SubAgent(simple_tuple)
        assert agent.tuple == simple_tuple

    @pytest.mark.asyncio
    async def test_execute_without_tools(self, simple_tuple):
        """Execute with simple prompt, no tools."""
        agent = SubAgent(simple_tuple)

        # Mock OpenAI client response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.choices[0].message.tool_calls = None

        with patch.object(agent, "client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await agent.execute()

        assert isinstance(result, Observation)
        assert result.result_summary == "Hello, world!"
        assert result.error_logs == []

    @pytest.mark.asyncio
    async def test_execute_with_tools(self, tuple_with_tools):
        """Execute with tools that get invoked."""
        agent = SubAgent(tuple_with_tools)

        # Mock OpenAI response with tool call
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="echo",
                    arguments='{"message": "test"}',
                )
            )
        ]

        with patch.object(agent, "client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await agent.execute()

        assert isinstance(result, Observation)
        assert "echo" in result.result_summary
        assert result.artifacts["echo"] == "Echo: test"

    @pytest.mark.asyncio
    async def test_execute_with_tool_error(self, tuple_with_tools):
        """Tool execution errors are captured in error_logs."""
        agent = SubAgent(tuple_with_tools)

        # Mock OpenAI response with calculator tool call (divide by zero)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="calculator",
                    arguments='{"operation": "divide", "a": 5, "b": 0}',
                )
            )
        ]

        with patch.object(agent, "client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await agent.execute()

        assert isinstance(result, Observation)
        assert len(result.error_logs) > 0
        assert "calculator" in result.error_logs[0]

    @pytest.mark.asyncio
    async def test_execute_handles_llm_errors(self, simple_tuple):
        """LLM errors are caught and returned in Observation."""
        agent = SubAgent(simple_tuple)

        with patch.object(agent, "client") as mock_client:
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API error")
            )

            result = await agent.execute()

        assert isinstance(result, Observation)
        assert "Execution failed" in result.result_summary
        assert len(result.error_logs) > 0

    def test_build_prompt_without_context(self, simple_tuple):
        """Prompt building without context."""
        agent = SubAgent(simple_tuple)
        prompt = agent.tuple.build_prompt()
        assert prompt == "Say hello"

    def test_build_prompt_with_context(self, model_config):
        """Prompt building with context."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            context="Numbers: 1, 2, 3",
            model=model_config,
        )
        agent = SubAgent(tuple_def)
        prompt = agent.tuple.build_prompt()
        assert "Calculate" in prompt
        assert "Numbers: 1, 2, 3" in prompt

    def test_find_tool_by_name(self, tuple_with_tools):
        """Can find tools by name."""
        agent = SubAgent(tuple_with_tools)
        echo_tool = agent._find_tool("echo")
        assert echo_tool is not None
        assert echo_tool.name == "echo"

    def test_find_nonexistent_tool_returns_none(self, tuple_with_tools):
        """Finding nonexistent tool returns None."""
        agent = SubAgent(tuple_with_tools)
        tool = agent._find_tool("nonexistent")
        assert tool is None
```

##### 3. Update Core Module Exports

**File**: `aorchestra/core/__init__.py`
**Changes**: Add SubAgent to exports

```python
"""Core agent abstraction module."""

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.core.agents import SubAgent

__all__ = [
    "AgentTuple",
    "Observation",
    "SubAgent",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass: `pytest tests/test_agents.py -v`
- [ ] Test coverage ≥80% for agents module
- [ ] SubAgent executes with simple prompts (no tools)
- [ ] SubAgent executes with tool calls (mocked LLM response)
- [ ] Tool errors captured in error_logs
- [ ] LLM errors handled gracefully
- [ ] Prompt building works correctly

##### Manual Verification:

- [ ] Review SubAgent.execute() flow - builds prompt, calls LLM, handles tools
- [ ] Verify isolation - SubAgent only accesses its assigned context/tools
- [ ] Test with mock tools in Python REPL
- [ ] Review error handling - all exceptions caught, returned in Observation
- [ ] Verify async execution works with asyncio.run()
- [ ] Confirm Observation structure matches requirements

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 4.

---

### Phase 4: AgentFactory

#### Overview

Implement AgentFactory that creates SubAgent instances from AgentTuples. The factory validates the tuple configuration and provides a clean interface for the orchestrator (item 002) to spawn sub-agents dynamically.

#### Changes Required:

##### 1. AgentFactory Implementation

**File**: `aorchestra/core/factory.py` (NEW)
**Changes**: Implement AgentFactory for sub-agent instantiation

```python
"""AgentFactory for creating SubAgent instances.

AgentFactory provides a clean interface for spawning sub-agents
from 4-tuples. It validates configurations and handles errors.
"""

import logging
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.agents import SubAgent
from aorchestra.tools.base import validate_tool

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating SubAgent instances from AgentTuples.

    The factory validates the tuple configuration and ensures tools
    are valid before creating a SubAgent. Used by the Orchestrator
    to spawn sub-agents dynamically.
    """

    def create(self, tuple_def: AgentTuple) -> SubAgent:
        """Create a SubAgent from an AgentTuple.

        Validates the tuple configuration and instantiates a SubAgent.

        Args:
            tuple_def: The 4-tuple defining the sub-agent.

        Returns:
            A configured SubAgent instance.

        Raises:
            ValueError: If the tuple configuration is invalid.
            TypeError: If tools don't implement the Tool protocol.
        """
        self._validate_tuple(tuple_def)
        logger.info(f"Creating SubAgent for instruction: {tuple_def.instruction[:50]}...")
        return SubAgent(tuple_def)

    def _validate_tuple(self, tuple_def: AgentTuple) -> None:
        """Validate an AgentTuple configuration.

        Args:
            tuple_def: The tuple to validate.

        Raises:
            ValueError: If validation fails.
            TypeError: If tools are invalid.
        """
        # Pydantic validates basic structure, but we add custom checks
        if not tuple_def.instruction.strip():
            raise ValueError("AgentTuple instruction cannot be empty")

        # Validate tools implement Tool protocol
        for i, tool in enumerate(tuple_def.tools):
            try:
                validate_tool(tool)
            except TypeError as e:
                raise TypeError(
                    f"Tool at index {i} is invalid: {e}"
                ) from e

        # Validate model configuration
        if not tuple_def.model.name:
            raise ValueError("Model name cannot be empty")
        if not tuple_def.model.api_base:
            raise ValueError("Model api_base cannot be empty")

        logger.debug("AgentTuple validation successful")

    async def create_and_execute(self, tuple_def: AgentTuple):
        """Convenience method to create and execute a SubAgent.

        Args:
            tuple_def: The 4-tuple defining the sub-agent.

        Returns:
            Observation from the sub-agent execution.
        """
        agent = self.create(tuple_def)
        return await agent.execute()
```

##### 2. AgentFactory Tests

**File**: `tests/test_factory.py` (NEW)
**Changes**: Unit tests for AgentFactory

```python
"""Tests for AgentFactory."""

import pytest
from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool


class TestAgentFactory:
    """Test AgentFactory validation and creation."""

    @pytest.fixture
    def factory(self):
        """AgentFactory instance."""
        return AgentFactory()

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def valid_tuple(self, model_config):
        """Valid AgentTuple."""
        return AgentTuple(
            instruction="Test task",
            model=model_config,
        )

    def test_create_returns_subagent(self, factory, valid_tuple):
        """create() returns a SubAgent instance."""
        agent = factory.create(valid_tuple)
        assert agent.__class__.__name__ == "SubAgent"
        assert agent.tuple == valid_tuple

    def test_create_with_tools(self, factory, model_config):
        """create() works with tools."""
        tuple_def = AgentTuple(
            instruction="Calculate",
            tools=[CalculatorTool()],
            model=model_config,
        )
        agent = factory.create(tuple_def)
        assert len(agent.tuple.tools) == 1

    def test_create_with_empty_instruction_raises_error(self, factory, model_config):
        """Empty instruction raises ValueError."""
        # This should be caught by Pydantic validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            tuple_def = AgentTuple(
                instruction="   ",
                model=model_config,
            )
            factory.create(tuple_def)

    def test_create_with_invalid_tool_raises_error(self, factory, model_config):
        """Invalid tool raises TypeError."""
        tuple_def = AgentTuple(
            instruction="Test",
            tools=[{"not": "a tool"}],
            model=model_config,
        )
        with pytest.raises(TypeError, match="Tool at index 0 is invalid"):
            factory.create(tuple_def)

    def test_create_with_invalid_model_name_raises_error(self, factory, model_config):
        """Empty model name raises ValueError."""
        tuple_def = AgentTuple(
            instruction="Test",
            model=ModelConfig(name="", api_base="https://api.z.ai/v1"),
        )
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            factory.create(tuple_def)

    def test_create_with_invalid_api_base_raises_error(self, factory):
        """Empty api_base raises ValueError."""
        tuple_def = AgentTuple(
            instruction="Test",
            model=ModelConfig(name="glm-4.7", api_base=""),
        )
        with pytest.raises(ValueError, match="Model api_base cannot be empty"):
            factory.create(tuple_def)

    @pytest.mark.asyncio
    async def test_create_and_execute_convenience_method(self, factory, valid_tuple):
        """create_and_execute() creates agent and executes it."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock the SubAgent.execute method
        with patch("aorchestra.core.agents.SubAgent.execute") as mock_execute:
            mock_execute = AsyncMock()
            mock_observation = MagicMock()
            mock_observation.result_summary = "Test result"
            mock_execute.return_value = mock_observation

            # Need to patch SubAgent to return our mock
            with patch("aorchestra.core.factory.SubAgent") as MockSubAgent:
                mock_agent_instance = MagicMock()
                mock_agent_instance.execute = mock_execute
                MockSubAgent.return_value = mock_agent_instance

                result = await factory.create_and_execute(valid_tuple)

        assert result.result_summary == "Test result"
```

##### 3. Update Core Module Exports

**File**: `aorchestra/core/__init__.py`
**Changes**: Add AgentFactory to exports

```python
"""Core agent abstraction module."""

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.core.agents import SubAgent
from aorchestra.core.factory import AgentFactory

__all__ = [
    "AgentTuple",
    "Observation",
    "SubAgent",
    "AgentFactory",
]
```

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass: `pytest tests/test_factory.py -v`
- [ ] Test coverage ≥85% for factory module
- [ ] Factory creates valid SubAgent instances
- [ ] Factory validates tuple configurations
- [ ] Factory rejects invalid tools with clear error messages
- [ ] Factory rejects invalid model configurations
- [ ] create_and_execute() convenience method works

##### Manual Verification:

- [ ] Review AgentFactory.create() implementation
- [ ] Test validation with various configurations
- [ ] Verify error messages are clear and actionable
- [ ] Test with real tools in Python REPL
- [ ] Confirm factory is ready for item 002 integration

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 5.

---

### Phase 5: Z.ai Integration and Examples

#### Overview

Create example scripts demonstrating end-to-end usage of the 4-tuple agent abstraction. Configure Z.ai integration with proper API endpoints. Document usage patterns for downstream items (002-005). This phase validates the complete system works as intended.

#### Changes Required:

##### 1. Environment Configuration

**File**: `.env.example` (NEW)
**Changes**: Template for environment variables

```bash
# Z.ai API Configuration
# Get your API key from https://z.ai/
ZAI_API_KEY=your_api_key_here
ZAI_API_BASE=https://api.z.ai/v1

# Default model
ZAI_MODEL=glm-4.7
```

**File**: `aorchestra/config.py` (NEW)
**Changes**: Configuration loading from environment

```python
"""Configuration management for AOrchestra."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    zai_api_key: str
    zai_api_base: str
    zai_model: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            zai_api_key=os.getenv("ZAI_API_KEY", ""),
            zai_api_base=os.getenv("ZAI_API_BASE", "https://api.z.ai/v1"),
            zai_model=os.getenv("ZAI_MODEL", "glm-4.7"),
        )
```

##### 2. Example Scripts

**File**: `examples/basic_agent.py` (NEW)
**Changes**: Basic example demonstrating 4-tuple usage

```python
"""Basic example of using the 4-tuple agent abstraction.

This example shows how to:
1. Create an AgentTuple
2. Use AgentFactory to spawn a SubAgent
3. Execute the agent and get an Observation
"""

import asyncio
import logging

from aorchestra import AgentTuple, AgentFactory, Observation
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run a basic agent example."""

    # Configure the model (using mock for this example)
    model = ModelConfig(
        name="glm-4.7",
        api_base="https://api.z.ai/v1",
        api_key="dummy",  # Replace with real key for production
    )

    # Create a 4-tuple defining the sub-agent
    agent_tuple = AgentTuple(
        instruction="Calculate the sum of 15 and 27",
        tools=[CalculatorTool()],
        model=model,
    )

    # Use AgentFactory to create the sub-agent
    factory = AgentFactory()

    # For this example, we'll use a mock instead of real LLM
    # In production, you would do:
    # result = await factory.create_and_execute(agent_tuple)

    # Instead, let's demonstrate the structure:
    agent = factory.create(agent_tuple)
    logger.info(f"Created agent for instruction: {agent_tuple.instruction}")
    logger.info(f"Available tools: {[t.name for t in agent_tuple.tools]}")
    logger.info(f"Model: {agent_tuple.model.name}")

    # The agent.execute() would call the LLM here
    # For demo purposes, we'll just show the structure
    print("\n=== Agent Configuration ===")
    print(f"Instruction: {agent_tuple.instruction}")
    print(f"Prompt: {agent_tuple.build_prompt()}")
    print(f"Tools: {[t.name for t in agent_tuple.tools]}")
    print(f"Model: {agent_tuple.model.name}")

    print("\n=== Example Observation Structure ===")
    demo_observation = Observation(
        result_summary="Calculator tool executed successfully",
        artifacts={"calculator": 42.0},
        error_logs=[],
    )
    print(f"Result Summary: {demo_observation.result_summary}")
    print(f"Artifacts: {demo_observation.artifacts}")
    print(f"Error Logs: {demo_observation.error_logs}")


if __name__ == "__main__":
    asyncio.run(main())
```

**File**: `examples/with_tools.py` (NEW)
**Changes**: Example showing tool usage

```python
"""Example of sub-agent with multiple tools."""

import asyncio
import logging

from aorchestra import AgentTuple, AgentFactory
from aorchestra.models.config import ModelConfig
from aorchestra.tools.mock import EchoTool, CalculatorTool

logging.basicConfig(level=logging.INFO)


async def main():
    """Demonstrate sub-agent with multiple tools."""

    # Configure model
    model = ModelConfig(
        name="glm-4.7",
        api_base="https://api.z.ai/v1",
        api_key="dummy",
    )

    # Create tuple with multiple tools
    agent_tuple = AgentTuple(
        instruction="Calculate 15 * 3, then echo the result",
        tools=[CalculatorTool(), EchoTool()],
        model=model,
    )

    factory = AgentFactory()
    agent = factory.create(agent_tuple)

    print("=== Multi-Tool Agent ===")
    print(f"Instruction: {agent_tuple.instruction}")
    print(f"Tools available:")
    for tool in agent_tuple.tools:
        print(f"  - {tool.name}: {tool.description}")

    # Test tools directly
    print("\n=== Testing Tools Directly ===")
    calc = CalculatorTool()
    result = await calc.execute(operation="multiply", a=15, b=3)
    print(f"Calculator.multiply(15, 3) = {result}")

    echo = EchoTool()
    result = await echo.execute(message=f"The result is {result}")
    print(f"Echo: {result}")


if __name__ == "__main__":
    asyncio.run(main())
```

##### 3. Update Dependencies

**File**: `pyproject.toml`
**Changes**: Add python-dotenv for environment config

```toml
dependencies = [
    "pydantic>=2.0,<3.0",
    "openai>=1.0,<2.0",
    "python-dotenv>=1.0,<2.0",
]
```

**File**: `requirements.txt`
**Changes**: Add python-dotenv

```
pydantic==2.7.4
openai==1.54.0
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
pytest-mock==3.14.0
```

##### 4. Update Root Package Exports

**File**: `aorchestra/__init__.py`
**Changes**: Add AgentFactory to exports

```python
"""AOrchestra: Open Implementation of Agentic Orchestration.

Any agent is a dynamically instantiable 4-tuple:
    Φ = (Instruction, Context, Tools, Model)
"""

__version__ = "0.1.0"

from aorchestra.core import (
    AgentTuple,
    SubAgent,
    AgentFactory,
    Observation,
)

__all__ = [
    "__version__",
    "AgentTuple",
    "SubAgent",
    "AgentFactory",
    "Observation",
]
```

##### 5. Documentation

**File**: `docs/001-api-reference.md` (NEW)
**Changes**: API reference for item 001

```markdown
# Item 001: Core 4-Tuple Agent Abstraction - API Reference

## Overview

Item 001 implements the foundational 4-tuple agent abstraction:
```
Φ = (Instruction, Context, Tools, Model)
```

## Core Components

### AgentTuple

The 4-tuple dataclass defining an agent configuration.

```python
from aorchestra import AgentTuple, ModelConfig

tuple = AgentTuple(
    instruction="Solve this task",
    context="Relevant context information",
    tools=[tool1, tool2],
    model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
)
```

### Observation

Result structure returned by SubAgent execution.

```python
{
    "result_summary": "Task completed successfully",
    "artifacts": {"output": "generated content"},
    "error_logs": []
}
```

### AgentFactory

Factory for creating SubAgent instances.

```python
from aorchestra import AgentFactory

factory = AgentFactory()
agent = factory.create(agent_tuple)
result = await agent.execute()
```

## Usage Examples

See `examples/basic_agent.py` and `examples/with_tools.py` for complete examples.
```

#### Success Criteria:

##### Automated Verification:

- [ ] Example scripts run without errors: `python examples/basic_agent.py` and `python examples/with_tools.py`
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Test coverage ≥80% overall: `pytest --cov=aorchestra --cov-report=html`
- [ ] Package installs correctly: `pip install -e .`
- [ ] All imports work: `python -c "from aorchestra import AgentTuple, SubAgent, AgentFactory, Observation"`

##### Manual Verification:

- [ ] Run basic_agent.py and verify output shows correct structure
- [ ] Run with_tools.py and verify tool execution
- [ ] Test with real Z.ai API (if credentials available)
- [ ] Verify AgentTuple serialization works
- [ ] Confirm Observation structure matches requirements
- [ ] Review documentation for clarity
- [ ] Test error handling with invalid configurations
- [ ] Verify async execution works with asyncio.run()
- [ ] Confirm all acceptance criteria from item.json are met

**Note**: Complete all automated verification, then perform final manual review before marking item complete.

---

## Testing Strategy

### Unit Tests:

- **Data Models** (tests/test_tuples.py, tests/test_models.py, tests/test_observations.py):
  - Pydantic validation for all fields
  - Edge cases: empty strings, None values, out-of-range numbers
  - JSON serialization/deserialization
  - Field validation errors with clear messages

- **Tool Protocol** (tests/test_tools.py):
  - Valid tool objects pass validation
  - Invalid objects raise TypeError
  - Mock tools (EchoTool, CalculatorTool, ErrorTool) execute correctly
  - Tool error handling

- **SubAgent** (tests/test_agents.py):
  - Prompt building from instruction + context
  - LLM calling with mocked OpenAI client
  - Tool invocation handling
  - Error capture in Observation.error_logs
  - Isolation (no shared state between agents)

- **AgentFactory** (tests/test_factory.py):
  - Creates SubAgent from valid AgentTuple
  - Validates configurations
  - Rejects invalid tools/models with clear errors
  - create_and_execute() convenience method

### Integration Tests:

- **End-to-End Flow**:
  - Create AgentTuple → AgentFactory.create() → SubAgent.execute() → Observation
  - Test with tools and without tools
  - Verify Observation structure
  - Test error scenarios (LLM failure, tool failure)

- **Async Execution**:
  - Multiple agents run concurrently
  - No blocking operations
  - Proper async/await patterns

### Manual Testing Steps:

1. **Install Package**:
   ```powershell
   pip install -e .
   ```

2. **Run Unit Tests**:
   ```powershell
   pytest tests/ -v
   ```

3. **Run Example Scripts**:
   ```powershell
   python examples/basic_agent.py
   python examples/with_tools.py
   ```

4. **Test Real Z.ai API** (optional, requires credentials):
   - Set ZAI_API_KEY in .env
   - Modify example to use real API calls
   - Verify GLM-4.7 responses
   - Test tool calling support

5. **Verify Serialization**:
   ```python
   from aorchestra import AgentTuple, ModelConfig
   import json

   tuple = AgentTuple(
       instruction="Test",
       model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1")
   )

   # Serialize
   json_str = tuple.model_dump_json()

   # Deserialize
   restored = AgentTuple.model_validate_json(json_str)
   ```

6. **Test Error Handling**:
   - Invalid AgentTuple configurations
   - Missing required fields
   - Invalid tools
   - LLM API failures
   - Tool execution failures

## Migration Notes

N/A - Greenfield implementation, no existing code to migrate.

## References

- Research: `C:\Users\strau\clawd\aorchestra\.wreckit\items\001-core-4tuple-agent-abstraction\research.md`
- Item Definition: `C:\Users\strau\clawd\aorchestra\.wreckit\items\001-core-4tuple-agent-abstraction\item.json`
- README: `C:\Users\strau\clawd\aorchestra\README.md` (lines 5-7 define 4-tuple)
- Downstream Dependencies:
  - Item 002: `C:\Users\strau\clawd\aorchestra\.wreckit\items\002-orchestrator-delegate-finish\item.json`
  - Item 003: `C:\Users\strau\clawd\aorchestra\.wreckit\items\003-dynamic-context-tool-selection\item.json`
  - Item 004: `C:\Users\strau\clawd\aorchestra\.wreckit\items\004-cost-aware-model-routing\item.json`
