# Orchestrator with Delegate and Finish Implementation Plan

## Implementation Plan Title

Orchestrator: LLM-Governed Task Delegation with State History Tracking

## Overview

Implement the central Orchestrator class that serves as the decision-making brain of AOrchestra. The orchestrator decomposes complex tasks into subtasks, delegates to dynamically-created sub-agents (via 4-tuples), and synthesizes their observations into a final answer. It has exactly two system actions: **Delegate(Φ)** which spawns a sub-agent and collects its observation, and **Finish(y)** which terminates with a final answer. The orchestrator uses an LLM to decide at each step whether to Delegate or Finish, maintaining a state history of all delegations and observations.

This implementation builds on the completed Item 001 foundation (AgentTuple, SubAgent, Observation, AgentFactory) and follows established patterns: Pydantic models, async-first design, and OpenAI-compatible LLM integration.

## Current State

**What exists (Item 001 - complete):**
- `aorchestra/core/tuples.py` - AgentTuple dataclass with instruction, context, tools, model fields
- `aorchestra/core/agents.py` - SubAgent class with async execution
- `aorchestra/core/observations.py` - Observation result structure with result_summary, artifacts, error_logs
- `aorchestra/core/factory.py` - AgentFactory for creating and executing sub-agents
- `aorchestra/models/config.py` - ModelConfig for LLM configuration
- `aorchestra/tools/base.py` - Tool protocol interface

**What's missing:**
- Orchestrator class implementing the decision-making loop
- OrchestratorState model for tracking delegation history
- Action models (DelegateAction, FinishAction) for structured LLM output
- LLM-based action selection using OpenAI function calling
- State transition logic integrating observations into history
- Delegation flow using AgentFactory.create_and_execute()
- Finish action terminating with final answer

**Key constraints discovered:**
1. Must use OpenAI function calling (not parsing) for reliable structured output (research.md)
2. Must implement max_steps constraint to prevent infinite loops (item.json)
3. Must maintain state history of all delegations and observations (item.json)
4. Must never directly execute environment actions - only Delegate and Finish (item.json)
5. For item 002, tool selection is simplified (all tools or empty list), enhanced in item 003 (research.md)
6. For item 002, use default model from config, ModelRegistry added in item 004 (research.md)

## Desired End State

A fully functional Orchestrator class that:

1. **Accepts a goal string** and orchestrates task completion through delegation
2. **Maintains OrchestratorState** with step count, delegation history, and goal
3. **Uses LLM to decide actions** - choose between Delegate and Finish at each step
4. **Executes Delegate action** by:
   - Creating an AgentTuple from the DelegateAction parameters
   - Calling AgentFactory.create_and_execute(tuple)
   - Capturing the Observation in state history
5. **Executes Finish action** by returning the final answer
6. **Respects max_steps constraint** - terminates if step limit reached
7. **Captures all errors** in state without failing the orchestrator
8. **Supports async execution** throughout

**Verification:**
- Unit tests demonstrate state transitions with mocked LLM/factory
- Integration tests show correct action selection with real LLM
- End-to-end tests complete full delegation workflows
- All tests pass: `pytest tests/test_orchestrator.py -v`
- Type checking passes: `mypy aorchestra/orchestrator/`

### Key Discoveries:

- AgentFactory already has `create_and_execute()` method (factory.py:75) perfect for delegation
- Observation uses Pydantic (observations.py:13) enabling JSON serialization for state history
- AgentTuple.build_prompt() (tuples.py:40) can be reused for context construction
- OpenAI function calling is required for reliable structured output (research.md decision)
- Testing pattern from item 001 uses pytest.mark.asyncio and mock clients (test_factory.py:95)
- Error handling pattern: capture in Observation.error_logs, don't raise (agents.py:42-50)

## What We're NOT Doing

To prevent scope creep, the following are explicitly OUT of scope for item 002:

- **Tool selection logic** - Item 003 will add ToolRegistry with intelligent filtering. For item 002, pass all tools or let LLM specify tool names as simple strings.
- **Model selection logic** - Item 004 will add ModelRegistry with cost-aware routing. For item 002, use a single default model configured in Orchestrator.__init__.
- **Parallel delegation** - Sequential delegation only. Parallel delegation (asyncio.gather) is a future enhancement.
- **Context window management** - Pass full history to LLM (assume small scale). Summarization/limiting is a future enhancement.
- **User intervention/stepping** - No interactive mode. Fully automated execution.
- **Visualization/dashboard** - No UI or observation visualization.
- **Cost tracking** - Item 004 will add cost accounting per model.
- **Evaluation framework** - Item 005 will add benchmark tasks and metrics.
- **Multi-agent coordination** - Orchestrator manages one sub-agent at a time (sequential). Multi-agent scenarios are future work.
- **Checkpointing/resume** - No state persistence. Each run starts fresh.

## Implementation Approach

**High-level strategy:** Build the Orchestrator as an async state machine with LLM-based action selection. The orchestrator maintains a history of all delegations and uses this context to inform subsequent decisions. OpenAI function calling ensures reliable structured output for action selection.

**Phase 1: Core Data Models** (orchestrator/state.py, orchestrator/actions.py)
- Create Pydantic models for OrchestratorState, Delegation, DelegateAction, FinishAction
- These models enable type safety, validation, and JSON serialization
- Independent of orchestrator logic, can be tested immediately

**Phase 2: Orchestrator Class Structure** (core/orchestrator.py)
- Create Orchestrator class with state machine skeleton
- Implement main loop with max_steps constraint
- Stub _decide_action() to return test actions
- Implement _delegate() and _finish() helper methods
- Implement state transition logic
- Test with mocked actions (no LLM yet)

**Phase 3: LLM-Based Decision Making** (orchestrator/prompts.py + orchestrator.py)
- Design system prompt for action selection
- Implement _decide_action() with OpenAI function calling
- Define "delegate_subagent" and "finish_task" functions
- Parse LLM response into DelegateAction or FinishAction
- Build context from state history for LLM prompt
- Test with mocked LLM responses

**Phase 4: Delegation Integration** (orchestrator.py)
- Connect _delegate() to AgentFactory.create_and_execute()
- Build AgentTuple from DelegateAction parameters
- Pass relevant history as context to sub-agents
- Capture Observation in state history
- Test with mocked factory

**Phase 5: End-to-End Testing**
- Integration tests with real LLM (requires API keys)
- Test single-delegation scenarios
- Test multi-delegation scenarios
- Test max_steps termination
- Test error handling

**Architectural decisions:**
1. Package structure: New `aorchestra/orchestrator/` module for orchestrator-specific code, `aorchestra/core/orchestrator.py` for main class
2. State model: Delegation records (tuple, observation, step, timestamp) accumulated in OrchestratorState.history
3. Action models: DelegateAction (instruction, context, tools, reasoning) and FinishAction (answer, reasoning) for structured LLM output
4. LLM decision: Use OpenAI function calling with two functions, force choice of exactly one
5. Error handling: Capture in state, continue execution, never raise from orchestrator

---

## Phases

### Phase 1: Core Data Models

#### Overview

Create Pydantic models for orchestrator state and actions. These models provide type safety, validation, and JSON serialization for the orchestrator's internal state and LLM communication.

#### Changes Required:

##### 1. orchestrator/state.py

**File**: `aorchestra/orchestrator/state.py`
**Changes**: Create new file with OrchestratorState and Delegation models

```python
"""Orchestrator state models."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation


class Delegation(BaseModel):
    """Record of a single delegation step.

    Tracks the tuple used to create a sub-agent, the observation
    returned from execution, and metadata (step number, timestamp).
    """

    step: int = Field(
        ...,
        description="Step number when this delegation occurred",
    )
    tuple: AgentTuple = Field(
        ...,
        description="The 4-tuple used to create the sub-agent",
    )
    observation: Observation = Field(
        ...,
        description="Observation returned from sub-agent execution",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of when the delegation completed",
    )


class OrchestratorState(BaseModel):
    """State of the orchestrator's execution.

    Tracks the current goal, step count, delegation history,
    and execution constraints.
    """

    goal: str = Field(
        ...,
        description="The overall goal the orchestrator is working toward",
    )
    step: int = Field(
        default=0,
        description="Current step number (starts at 0)",
        ge=0,
    )
    history: list[Delegation] = Field(
        default_factory=list,
        description="Chronological history of all delegations and observations",
    )
    max_steps: int = Field(
        default=20,
        description="Maximum number of delegation steps before forced termination",
        ge=1,
    )
    current_answer: Optional[str] = Field(
        default=None,
        description="Current best answer (accumulated from observations)",
    )

    @property
    def is_finished(self) -> bool:
        """Check if orchestrator has reached max_steps."""
        return self.step >= self.max_steps

    def add_delegation(self, delegation: Delegation) -> None:
        """Add a delegation to history and increment step."""
        self.history.append(delegation)
        self.step += 1
```

##### 2. orchestrator/actions.py

**File**: `aorchestra/orchestrator/actions.py`
**Changes**: Create new file with DelegateAction and FinishAction models

```python
"""Action models for orchestrator decision-making."""

from pydantic import BaseModel, Field


class DelegateAction(BaseModel):
    """Action to delegate a subtask to a sub-agent.

    The LLM generates this action when it determines that a subtask
    should be delegated to a dynamically-created sub-agent.
    """

    instruction: str = Field(
        ...,
        description="Instruction for the sub-agent (what task to perform)",
    )
    context: str = Field(
        default="",
        description="Relevant context to pass to the sub-agent",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Names of tools to include (empty list = no tools)",
    )
    reasoning: str = Field(
        ...,
        description="Why this delegation is necessary",
    )


class FinishAction(BaseModel):
    """Action to finish with a final answer.

    The LLM generates this action when it determines that sufficient
    information has been gathered to answer the goal.
    """

    answer: str = Field(
        ...,
        description="The final answer to the orchestrator's goal",
    )
    reasoning: str = Field(
        ...,
        description="Why the task is complete and this answer is sufficient",
    )
```

##### 3. orchestrator/__init__.py

**File**: `aorchestra/orchestrator/__init__.py`
**Changes**: Create module init file

```python
"""Orchestrator module for task delegation and decision-making."""

from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction

__all__ = [
    "OrchestratorState",
    "Delegation",
    "DelegateAction",
    "FinishAction",
]
```

##### 4. tests/test_orchestrator_models.py

**File**: `tests/test_orchestrator_models.py`
**Changes**: Create unit tests for state and action models

```python
"""Tests for orchestrator state and action models."""

import pytest
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction
from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig


class TestOrchestratorState:
    """Test OrchestratorState model."""

    def test_create_state(self):
        """Create a valid OrchestratorState."""
        state = OrchestratorState(goal="Test goal")
        assert state.goal == "Test goal"
        assert state.step == 0
        assert state.history == []
        assert state.max_steps == 20
        assert state.is_finished is False

    def test_max_steps_custom(self):
        """Custom max_steps constraint."""
        state = OrchestratorState(goal="Test", max_steps=5)
        assert state.max_steps == 5

    def test_is_finished_when_step_equals_max(self):
        """is_finished returns True when step == max_steps."""
        state = OrchestratorState(goal="Test", max_steps=2, step=2)
        assert state.is_finished is True

    def test_add_delegation_increments_step(self):
        """add_delegation adds to history and increments step."""
        state = OrchestratorState(goal="Test")
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Test",
                model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
            ),
            observation=Observation(result_summary="Done"),
        )
        state.add_delegation(delegation)
        assert state.step == 1
        assert len(state.history) == 1


class TestDelegateAction:
    """Test DelegateAction model."""

    def test_create_delegate_action(self):
        """Create a valid DelegateAction."""
        action = DelegateAction(
            instruction="Calculate something",
            reasoning="Need computation",
        )
        assert action.instruction == "Calculate something"
        assert action.context == ""
        assert action.tools == []
        assert action.reasoning == "Need computation"

    def test_delegate_action_with_all_fields(self):
        """Create DelegateAction with all fields."""
        action = DelegateAction(
            instruction="Search web",
            context="User query: X",
            tools=["search", "calculator"],
            reasoning="Need external data",
        )
        assert len(action.tools) == 2


class TestFinishAction:
    """Test FinishAction model."""

    def test_create_finish_action(self):
        """Create a valid FinishAction."""
        action = FinishAction(
            answer="The answer is 42",
            reasoning="Calculation complete",
        )
        assert action.answer == "The answer is 42"
        assert action.reasoning == "Calculation complete"


class TestDelegation:
    """Test Delegation model."""

    @pytest.fixture
    def sample_tuple(self):
        """Sample AgentTuple."""
        return AgentTuple(
            instruction="Test task",
            model=ModelConfig(name="glm-4.7", api_base="https://api.z.ai/v1"),
        )

    @pytest.fixture
    def sample_observation(self):
        """Sample Observation."""
        return Observation(result_summary="Task completed")

    def test_create_delegation(self, sample_tuple, sample_observation):
        """Create a valid Delegation."""
        delegation = Delegation(
            step=0,
            tuple=sample_tuple,
            observation=sample_observation,
        )
        assert delegation.step == 0
        assert delegation.tuple == sample_tuple
        assert delegation.observation == sample_observation
        assert delegation.timestamp  # Non-empty timestamp

    def test_delegation_serialization(self, sample_tuple, sample_observation):
        """Delegation can be serialized to JSON."""
        delegation = Delegation(
            step=0,
            tuple=sample_tuple,
            observation=sample_observation,
        )
        json_str = delegation.model_dump_json()
        assert "step" in json_str
        assert "timestamp" in json_str
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator_models.py -v`
- [ ] Type checking passes: `mypy aorchestra/orchestrator/`
- [ ] Models serialize to JSON: Test serialization in unit tests
- [ ] All validation rules work: Test edge cases (empty instruction, negative step, etc.)

##### Manual Verification:

- [ ] Review model fields match requirements from item.json
- [ ] Verify Delegation captures all necessary info (tuple, observation, step, timestamp)
- [ ] Verify OrchestratorState tracks goal, step, history, max_steps
- [ ] Verify action models match LLM output requirements

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 2.

---

### Phase 2: Orchestrator Class Structure

#### Overview

Create the Orchestrator class with the main decision loop and state machine skeleton. Implement the core flow including state transitions, step counting, and action execution, but use a stub for LLM decision-making (to be implemented in Phase 3).

#### Changes Required:

##### 1. core/orchestrator.py

**File**: `aorchestra/core/orchestrator.py`
**Changes**: Create new Orchestrator class

```python
"""Orchestrator for task delegation and decision-making."""

import logging
from typing import Optional
from openai import AsyncOpenAI
from aorchestra.core.factory import AgentFactory
from aorchestra.core.tuples import AgentTuple
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.state import OrchestratorState, Delegation
from aorchestra.orchestrator.actions import DelegateAction, FinishAction

logger = logging.getLogger(__name__)


class Orchestrator:
    """Central orchestrator that delegates tasks to sub-agents.

    The orchestrator maintains a state history of all delegations and
    observations, and uses an LLM to decide at each step whether to
    Delegate (spawn a sub-agent) or Finish (return final answer).

    The orchestrator never directly executes environment actions -
    it only performs Delegate and Finish system actions.
    """

    def __init__(
        self,
        model: ModelConfig,
        factory: Optional[AgentFactory] = None,
        max_steps: int = 20,
    ):
        """Initialize the orchestrator.

        Args:
            model: Model configuration for the orchestrator's LLM.
            factory: AgentFactory for creating sub-agents. If None, creates default.
            max_steps: Maximum number of delegation steps (prevents infinite loops).
        """
        self.model = model
        self.factory = factory or AgentFactory()
        self.max_steps = max_steps
        self.client = AsyncOpenAI(**model.to_openai_kwargs())
        self.state: Optional[OrchestratorState] = None

    async def run(self, goal: str) -> str:
        """Run the orchestrator to complete a goal.

        Args:
            goal: The goal to accomplish.

        Returns:
            The final answer when the orchestrator finishes.

        Raises:
            RuntimeError: If max_steps is reached without finishing.
        """
        # Initialize state
        self.state = OrchestratorState(goal=goal, max_steps=self.max_steps)

        # Main decision loop
        while not self.state.is_finished:
            # Decide next action (using LLM)
            action = await self._decide_action()

            # Execute the action
            if isinstance(action, FinishAction):
                logger.info(f"Finishing with answer: {action.answer[:50]}...")
                return action.answer

            # Delegate action
            observation = await self._delegate(action)
            self._integrate_observation(action, observation)

        # Max steps reached
        raise RuntimeError(
            f"Orchestrator reached max_steps ({self.max_steps}) without finishing"
        )

    async def _decide_action(self) -> DelegateAction | FinishAction:
        """Decide the next action using the LLM.

        This is a stub for Phase 2. Phase 3 will implement the actual
        LLM-based decision making.

        Args:
            context: Current context for decision making.

        Returns:
            Either a DelegateAction or FinishAction.
        """
        # STUB: Return a dummy FinishAction for testing
        # Phase 3 will implement actual LLM decision making
        return FinishAction(
            answer="Stub answer",
            reasoning="This is a stub - will be replaced with LLM decision",
        )

    async def _delegate(self, action: DelegateAction) -> Observation:
        """Delegate a subtask to a sub-agent.

        Creates a 4-tuple from the DelegateAction, spawns a sub-agent
        via AgentFactory, and returns the observation.

        Args:
            action: The DelegateAction specifying the subtask.

        Returns:
            Observation from the sub-agent execution.
        """
        # Build AgentTuple from action
        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=action.context,
            tools=[],  # TODO: Filter tools by action.tools in Phase 4
            model=self.model,  # Use same model for now (item 004 will add ModelRegistry)
        )

        logger.info(
            f"Delegating step {self.state.step}: {action.instruction[:50]}..."
        )

        # Execute via factory
        observation = await self.factory.create_and_execute(tuple_def)

        logger.info(
            f"Delegation completed: {observation.result_summary[:50]}..."
        )

        return observation

    def _integrate_observation(
        self,
        action: DelegateAction,
        observation: Observation,
    ) -> None:
        """Integrate an observation into the orchestrator state.

        Creates a Delegation record and adds it to the history.

        Args:
            action: The DelegateAction that was executed.
            observation: The Observation returned from the sub-agent.
        """
        # Reconstruct the tuple (we need it for the Delegation record)
        tuple_def = AgentTuple(
            instruction=action.instruction,
            context=action.context,
            tools=[],
            model=self.model,
        )

        delegation = Delegation(
            step=self.state.step,
            tuple=tuple_def,
            observation=observation,
        )

        self.state.add_delegation(delegation)

        logger.debug(
            f"State updated: step={self.state.step}, "
            f"history_length={len(self.state.history)}"
        )
```

##### 2. core/__init__.py

**File**: `aorchestra/core/__init__.py`
**Changes**: Export Orchestrator class

```python
"""Core agent abstraction module."""

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.core.agents import SubAgent
from aorchestra.core.factory import AgentFactory
from aorchestra.core.orchestrator import Orchestrator

__all__ = [
    "AgentTuple",
    "Observation",
    "SubAgent",
    "AgentFactory",
    "Orchestrator",
]
```

##### 3. tests/test_orchestrator.py

**File**: `tests/test_orchestrator.py`
**Changes**: Create unit tests for Orchestrator class (stub phase)

```python
"""Tests for Orchestrator class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import FinishAction


class TestOrchestrator:
    """Test Orchestrator state machine."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=5)

    def test_initialization(self, model_config):
        """Orchestrator initializes correctly."""
        orch = Orchestrator(model=model_config, max_steps=10)
        assert orch.model == model_config
        assert orch.max_steps == 10
        assert orch.state is None

    @pytest.mark.asyncio
    async def test_run_returns_finish_action_answer(self, orchestrator):
        """run() returns the answer from FinishAction."""
        # The stub _decide_action always returns FinishAction
        result = await orchestrator.run("Test goal")
        assert result == "Stub answer"

    @pytest.mark.asyncio
    async def test_run_initializes_state(self, orchestrator):
        """run() initializes orchestrator state."""
        await orchestrator.run("Test goal")
        assert orchestrator.state is not None
        assert orchestrator.state.goal == "Test goal"
        assert orchestrator.state.max_steps == 5

    @pytest.mark.asyncio
    async def test_max_steps_raises_error(self, orchestrator):
        """Max steps reached raises RuntimeError."""
        # Mock _decide_action to always delegate
        async def mock_delegate():
            from aorchestra.orchestrator.actions import DelegateAction
            return DelegateAction(
                instruction="Test",
                reasoning="Test",
            )

        orchestrator._decide_action = mock_delegate

        # Mock _delegate to return observation
        mock_obs = Observation(result_summary="Done")
        orchestrator._delegate = AsyncMock(return_value=mock_obs)

        with pytest.raises(RuntimeError, match="max_steps"):
            await orchestrator.run("Test goal")

    @pytest.mark.asyncio
    async def test_delegate_creates_tuple_and_executes(self, orchestrator):
        """_delegate creates AgentTuple and calls factory."""
        from aorchestra.orchestrator.actions import DelegateAction

        action = DelegateAction(
            instruction="Calculate 1+1",
            context="Math task",
            tools=[],
            reasoning="Need computation",
        )

        # Mock the factory
        mock_obs = Observation(result_summary="2")
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ) as mock_execute:
            observation = await orchestrator._delegate(action)

            assert observation.result_summary == "2"
            mock_execute.assert_called_once()
            # Verify the tuple was created correctly
            call_args = mock_execute.call_args[0][0]
            assert call_args.instruction == "Calculate 1+1"
            assert call_args.context == "Math task"

    @pytest.mark.asyncio
    async def test_integrate_observation_updates_state(self, orchestrator):
        """_integrate_observation adds delegation to history."""
        from aorchestra.orchestrator.actions import DelegateAction

        action = DelegateAction(
            instruction="Test",
            reasoning="Test",
        )
        observation = Observation(result_summary="Done")

        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test", max_steps=5)

        orchestrator._integrate_observation(action, observation)

        assert len(orchestrator.state.history) == 1
        assert orchestrator.state.step == 1
        assert orchestrator.state.history[0].observation.result_summary == "Done"
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator.py -v`
- [ ] Type checking passes: `mypy aorchestra/core/orchestrator.py`
- [ ] Orchestrator initializes correctly with model and max_steps
- [ ] run() method executes decision loop
- [ ] _delegate() creates AgentTuple and calls factory
- [ ] _integrate_observation() updates state history
- [ ] max_steps constraint raises RuntimeError when exceeded

##### Manual Verification:

- [ ] Review Orchestrator class structure matches architecture
- [ ] Verify state machine flow (while loop, action decision, execution)
- [ ] Verify error handling (max_steps raises, not infinite loop)
- [ ] Verify factory integration follows item 001 patterns
- [ ] Confirm stub _decide_action() is clearly marked for Phase 3

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 3.

---

### Phase 3: LLM-Based Decision Making

#### Overview

Implement the LLM-based decision-making logic using OpenAI function calling. The orchestrator will construct a prompt with the goal and delegation history, then use the LLM to decide between Delegate and Finish actions. This phase replaces the stub _decide_action() with actual LLM integration.

#### Changes Required:

##### 1. orchestrator/prompts.py

**File**: `aorchestra/orchestrator/prompts.py`
**Changes**: Create new file with system prompt and context builder

```python
"""Prompts and context construction for orchestrator LLM."""

from aorchestra.orchestrator.state import OrchestratorState


def build_system_prompt() -> str:
    """Build the system prompt for the orchestrator LLM.

    The system prompt explains the orchestrator's role and the two
    available actions (Delegate and Finish).
    """
    return """You are an orchestrator responsible for completing a complex goal by delegating subtasks to specialized sub-agents.

You have two actions available:

1. **Delegate**: Create a sub-agent to perform a specific subtask. Use this when:
   - The goal requires specialized work you cannot do directly
   - You need information gathering, computation, or external interaction
   - The goal can be decomposed into smaller steps

2. **Finish**: Return a final answer to the goal. Use this when:
   - You have sufficient information to answer the goal completely
   - Further delegations would not add value
   - The goal has been accomplished

IMPORTANT:
- You never execute tasks directly - you only delegate and finish
- Each delegation should have a clear, specific instruction
- Provide reasoning for your decision to help with transparency
- Be efficient - don't delegate unnecessarily
- Finish as soon as you have enough information to answer the goal
"""


def build_user_prompt(state: OrchestratorState) -> str:
    """Build the user prompt with current context.

    Includes the goal and relevant history of delegations and observations.

    Args:
        state: Current orchestrator state.

    Returns:
        Formatted prompt string.
    """
    lines = [
        f"**Goal:** {state.goal}",
        f"**Current Step:** {state.step} / {state.max_steps}",
    ]

    if state.history:
        lines.append("\n**Previous Delegations:**")
        for i, delegation in enumerate(state.history, 1):
            lines.append(f"\n{i. Step {delegation.step}}")
            lines.append(f"   - Instruction: {delegation.tuple.instruction}")
            lines.append(f"   - Result: {delegation.observation.result_summary}")

            # Include errors if any
            if delegation.observation.error_logs:
                lines.append(f"   - Errors: {', '.join(delegation.observation.error_logs)}")

    lines.append("\n**What is your next action?**")

    return "\n".join(lines)
```

##### 2. core/orchestrator.py (update _decide_action)

**File**: `aorchestra/core/orchestrator.py`
**Changes**: Replace stub _decide_action() with LLM-based implementation

```python
# Add import at top
from aorchestra.orchestrator import prompts


# Replace the stub _decide_action method with this implementation:

async def _decide_action(self) -> DelegateAction | FinishAction:
    """Decide the next action using the LLM.

    Constructs a prompt with the current goal and delegation history,
    then uses OpenAI function calling to get a structured action.

    Returns:
        Either a DelegateAction or FinishAction.
    """
    # Build prompts
    system_prompt = prompts.build_system_prompt()
    user_prompt = prompts.build_user_prompt(self.state)

    logger.debug(f"Deciding action for step {self.state.step}")

    # Call LLM with function calling
    response = await self.client.chat.completions.create(
        model=self.model.name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "delegate_subagent",
                    "description": "Delegate a subtask to a sub-agent",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instruction": {
                                "type": "string",
                                "description": "Instruction for the sub-agent",
                            },
                            "context": {
                                "type": "string",
                                "description": "Relevant context to pass to the sub-agent",
                            },
                            "tools": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tool names to include (empty = no tools)",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why this delegation is necessary",
                            },
                        },
                        "required": ["instruction", "reasoning"],
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "finish_task",
                    "description": "Finish the task with a final answer",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "answer": {
                                "type": "string",
                                "description": "The final answer to the goal",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Why the task is complete",
                            },
                        },
                        "required": ["answer", "reasoning"],
                    },
                }
            },
        ],
        tool_choice={"type": "function", "function": {"name": "delegate_subagent"}},
        temperature=0.7,
    )

    # Parse the function call
    message = response.choices[0].message
    if not message.tool_calls:
        raise ValueError("LLM did not return a tool call")

    tool_call = message.tool_calls[0]
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    if function_name == "delegate_subagent":
        logger.debug(f"LLM chose to Delegate: {arguments['instruction'][:50]}...")
        return DelegateAction(**arguments)
    elif function_name == "finish_task":
        logger.debug(f"LLM chose to Finish: {arguments['answer'][:50]}...")
        return FinishAction(**arguments)
    else:
        raise ValueError(f"Unknown function: {function_name}")
```

**Note**: Also need to add `import json` at the top of the file.

##### 3. tests/test_orchestrator_llm.py (new file)

**File**: `tests/test_orchestrator_llm.py`
**Changes**: Create tests for LLM decision making

```python
"""Tests for orchestrator LLM decision making."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.orchestrator import Orchestrator
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import DelegateAction, FinishAction


class TestLLMDecisionMaking:
    """Test LLM-based action selection."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=5)

    @pytest.mark.asyncio
    async def test_decide_action_parses_delegate_response(self, orchestrator):
        """_decide_action parses LLM delegate response."""
        # Initialize state
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="delegate_subagent",
                    arguments=json.dumps({
                        "instruction": "Calculate something",
                        "context": "Math task",
                        "tools": ["calculator"],
                        "reasoning": "Need computation",
                    }),
                )
            )
        ]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            action = await orchestrator._decide_action()

        assert isinstance(action, DelegateAction)
        assert action.instruction == "Calculate something"
        assert action.tools == ["calculator"]

    @pytest.mark.asyncio
    async def test_decide_action_parses_finish_response(self, orchestrator):
        """_decide_action parses LLM finish response."""
        from aorchestra.orchestrator.state import OrchestratorState
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="finish_task",
                    arguments=json.dumps({
                        "answer": "The answer is 42",
                        "reasoning": "Task complete",
                    }),
                )
            )
        ]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            action = await orchestrator._decide_action()

        assert isinstance(action, FinishAction)
        assert action.answer == "The answer is 42"

    @pytest.mark.asyncio
    async def test_decide_action_includes_history_in_prompt(self, orchestrator):
        """_decide_action includes delegation history in prompt."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.core.tuples import AgentTuple
        from aorchestra.core.observations import Observation

        # Create state with history
        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Previous task",
                model=orchestrator.model,
            ),
            observation=Observation(result_summary="Previous result"),
        )
        state.add_delegation(delegation)
        orchestrator.state = state

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="finish_task",
                    arguments=json.dumps({
                        "answer": "Done",
                        "reasoning": "Complete",
                    }),
                )
            )
        ]

        with patch.object(orchestrator.client, "chat", new=MagicMock()):
            orchestrator.client.chat.completions = MagicMock()
            orchestrator.client.chat.completions.create = AsyncMock(return_value=mock_response)

            await orchestrator._decide_action()

            # Verify prompt includes history
            call_args = orchestrator.client.chat.completions.create.call_args
            user_message = call_args[1]["messages"][1]["content"]
            assert "Previous Delegations" in user_message
            assert "Previous task" in user_message
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator_llm.py -v`
- [ ] Type checking passes: `mypy aorchestra/orchestrator/ aorchestra/core/orchestrator.py`
- [ ] _decide_action() calls LLM with function calling
- [ ] Delegate responses parsed correctly into DelegateAction
- [ ] Finish responses parsed correctly into FinishAction
- [ ] History is included in prompt construction

##### Manual Verification:

- [ ] Review system prompt is clear and comprehensive
- [ ] Verify function definitions match action models exactly
- [ ] Verify context builder formats history legibly
- [ ] Review error handling for malformed LLM responses
- [ ] Confirm tool_choice forces function calling (not free text)

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 4.

---

### Phase 4: Delegation Integration

#### Overview

Connect the orchestrator's delegation flow to the existing AgentFactory. Implement tool filtering (basic version for item 002), pass relevant history as context to sub-agents, and ensure observations are properly captured. This phase makes the orchestrator fully functional end-to-end.

#### Changes Required:

##### 1. core/orchestrator.py (update _delegate method)

**File**: `aorchestra/core/orchestrator.py`
**Changes**: Enhance _delegate() with context building and tool filtering

```python
# Update the _delegate method to build better context and filter tools

async def _delegate(self, action: DelegateAction) -> Observation:
    """Delegate a subtask to a sub-agent.

    Creates a 4-tuple from the DelegateAction, spawns a sub-agent
    via AgentFactory, and returns the observation.

    Args:
        action: The DelegateAction specifying the subtask.

    Returns:
        Observation from the sub-agent execution.
    """
    # Build context with relevant history
    context = self._build_context_for_subagent(action)

    # Filter tools (basic implementation for item 002)
    tools = self._filter_tools(action.tools)

    # Build AgentTuple
    tuple_def = AgentTuple(
        instruction=action.instruction,
        context=context,
        tools=tools,
        model=self.model,  # Use same model (item 004 will add ModelRegistry)
    )

    logger.info(
        f"Delegating step {self.state.step}: {action.instruction[:50]}..."
    )

    # Execute via factory
    try:
        observation = await self.factory.create_and_execute(tuple_def)
        logger.info(
            f"Delegation completed: {observation.result_summary[:50]}..."
        )
    except Exception as e:
        # Capture unexpected errors
        logger.error(f"Delegation failed: {e}")
        observation = Observation(
            result_summary=f"Delegation failed: {str(e)}",
        )
        observation.add_error(str(e))

    return observation


def _build_context_for_subagent(self, action: DelegateAction) -> str:
    """Build context string for a sub-agent.

    Includes the action's context plus relevant history.
    For item 002, include full history. Future items may summarize.

    Args:
        action: The DelegateAction being executed.

    Returns:
        Formatted context string.
    """
    parts = []

    # Add action-specific context
    if action.context:
        parts.append(action.context)

    # Add relevant history (last 3 observations for context)
    if self.state.history:
        parts.append("\n**Relevant Previous Work:**")
        recent_history = self.state.history[-3:]  # Last 3 delegations
        for delegation in recent_history:
            parts.append(
                f"- {delegation.observation.result_summary}"
            )

    return "\n".join(parts) if parts else ""


def _filter_tools(self, tool_names: list[str]) -> list:
    """Filter tools by name.

    For item 002, this is a simple placeholder. Item 003 will add
    ToolRegistry with intelligent tool selection.

    Args:
        tool_names: List of tool names to include.

    Returns:
        List of tool objects (empty list for item 002).
    """
    # Placeholder: Item 003 will implement ToolRegistry
    # For item 002, we don't have a tool registry yet
    # Return empty list (no tools) or all tools if requested
    if not tool_names:
        return []

    # TODO: Implement tool filtering in item 003
    logger.debug(f"Tool filtering not yet implemented, requested: {tool_names}")
    return []
```

##### 2. core/orchestrator.py (add imports)

**File**: `aorchestra/core/orchestrator.py`
**Changes**: No new imports needed, using existing ones

##### 3. tests/test_orchestrator_delegation.py (new file)

**File**: `tests/test_orchestrator_delegation.py`
**Changes**: Create integration tests for delegation flow

```python
"""Tests for orchestrator delegation integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig
from aorchestra.orchestrator.actions import DelegateAction, FinishAction


class TestDelegationFlow:
    """Test end-to-end delegation flow."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=5)

    @pytest.mark.asyncio
    async def test_delegate_with_factory(self, orchestrator):
        """_delegate creates agent via factory and returns observation."""
        from aorchestra.orchestrator.state import OrchestratorState

        # Initialize state
        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        action = DelegateAction(
            instruction="Calculate 1+1",
            context="Math needed",
            reasoning="Need computation",
        )

        # Mock factory
        mock_observation = Observation(
            result_summary="The answer is 2",
            artifacts={"result": 2},
        )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_observation)
        ) as mock_execute:
            result = await orchestrator._delegate(action)

            assert result.result_summary == "The answer is 2"
            mock_execute.assert_called_once()

            # Verify tuple structure
            call_args = mock_execute.call_args[0][0]
            assert call_args.instruction == "Calculate 1+1"
            assert "Math needed" in call_args.context

    @pytest.mark.asyncio
    async def test_delegate_includes_history_in_context(self, orchestrator):
        """_delegate includes relevant history in sub-agent context."""
        from aorchestra.orchestrator.state import OrchestratorState, Delegation
        from aorchestra.core.tuples import AgentTuple

        # Create state with history
        state = OrchestratorState(goal="Test goal", max_steps=5)
        delegation = Delegation(
            step=0,
            tuple=AgentTuple(
                instruction="Search for X",
                model=orchestrator.model,
            ),
            observation=Observation(result_summary="Found: X is 42"),
        )
        state.add_delegation(delegation)
        orchestrator.state = state

        action = DelegateAction(
            instruction="Calculate X + 10",
            reasoning="Need math",
        )

        mock_obs = Observation(result_summary="52")
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ) as mock_execute:
            await orchestrator._delegate(action)

            # Verify context includes history
            call_args = mock_execute.call_args[0][0]
            assert "Relevant Previous Work" in call_args.context
            assert "Found: X is 42" in call_args.context

    @pytest.mark.asyncio
    async def test_delegate_handles_factory_errors(self, orchestrator):
        """_delegate captures factory errors in observation."""
        from aorchestra.orchestrator.state import OrchestratorState

        orchestrator.state = OrchestratorState(goal="Test goal", max_steps=5)

        action = DelegateAction(
            instruction="Fail this",
            reasoning="Test error handling",
        )

        # Mock factory to raise exception
        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(side_effect=Exception("API error"))
        ):
            result = await orchestrator._delegate(action)

            # Should return observation with error, not raise
            assert "Delegation failed" in result.result_summary
            assert "API error" in result.error_logs[0]

    @pytest.mark.asyncio
    async def test_full_workflow_single_delegation(self, orchestrator):
        """Full workflow: delegate once then finish."""
        import json

        # Mock LLM to return delegate then finish
        delegate_response = MagicMock()
        delegate_response.choices = [MagicMock()]
        delegate_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="delegate_subagent",
                    arguments=json.dumps({
                        "instruction": "Get current time",
                        "reasoning": "Need time info",
                    }),
                )
            )
        ]

        finish_response = MagicMock()
        finish_response.choices = [MagicMock()]
        finish_response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name="finish_task",
                    arguments=json.dumps({
                        "answer": "The current time is 10:30 AM",
                        "reasoning": "Time retrieved",
                    }),
                )
            )
        ]

        # Mock factory
        mock_obs = Observation(result_summary="Time: 10:30 AM")

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(
                side_effect=[delegate_response, finish_response]
            )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ):
            result = await orchestrator.run("What time is it?")

        assert result == "The current time is 10:30 AM"
        assert orchestrator.state.step == 1
        assert len(orchestrator.state.history) == 1
```

#### Success Criteria:

##### Automated Verification:

- [ ] Tests pass: `pytest tests/test_orchestrator_delegation.py -v`
- [ ] Type checking passes: `mypy aorchestra/core/orchestrator.py`
- [ ] _delegate() calls factory.create_and_execute()
- [ ] Context building includes relevant history
- [ ] Factory errors captured in Observation.error_logs
- [ ] Full workflow test completes successfully

##### Manual Verification:

- [ ] Review _build_context_for_subagent() logic
- [ ] Verify error handling doesn't raise exceptions
- [ ] Confirm _filter_tools() is clearly marked as TODO for item 003
- [ ] Review full workflow test coverage

**Note**: Complete all automated verification, then pause for manual confirmation before proceeding to Phase 5.

---

### Phase 5: End-to-End Testing

#### Overview

Create comprehensive integration tests with real LLM calls (optional, requires API keys) and additional edge case tests. Ensure the orchestrator works correctly in various scenarios: single delegation, multiple delegations, max_steps termination, and error recovery.

#### Changes Required:

##### 1. tests/test_orchestrator_e2e.py (new file)

**File**: `tests/test_orchestrator_e2e.py`
**Changes**: Create end-to-end tests (with mocked LLM for determinism)

```python
"""End-to-end tests for Orchestrator.

These tests use mocked LLM responses for determinism but exercise
the full orchestrator workflow.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from aorchestra.core.orchestrator import Orchestrator
from aorchestra.core.observations import Observation
from aorchestra.models.config import ModelConfig


class TestOrchestratorE2E:
    """End-to-end orchestrator tests."""

    @pytest.fixture
    def model_config(self):
        """Default model config."""
        return ModelConfig(
            name="glm-4.7",
            api_base="https://api.z.ai/v1",
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=10)

    @pytest.mark.asyncio
    async def test_single_delegation_workflow(self, orchestrator):
        """Goal accomplished with a single delegation."""
        # LLM delegates then finishes
        delegate_response = self._mock_tool_call(
            "delegate_subagent",
            {
                "instruction": "Calculate 15 + 27",
                "reasoning": "Need arithmetic",
            }
        )
        finish_response = self._mock_tool_call(
            "finish_task",
            {
                "answer": "15 + 27 = 42",
                "reasoning": "Calculation complete",
            }
        )

        mock_obs = Observation(result_summary="The sum is 42", artifacts={"result": 42})

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(
                side_effect=[delegate_response, finish_response]
            )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ):
            result = await orchestrator.run("What is 15 + 27?")

        assert result == "15 + 27 = 42"
        assert orchestrator.state.step == 1
        assert len(orchestrator.state.history) == 1

    @pytest.mark.asyncio
    async def test_multi_delegation_workflow(self, orchestrator):
        """Goal accomplished with multiple delegations."""
        # LLM delegates three times then finishes
        responses = [
            self._mock_tool_call("delegate_subagent", {
                "instruction": "Search for population of Tokyo",
                "reasoning": "Need data",
            }),
            self._mock_tool_call("delegate_subagent", {
                "instruction": "Search for population of Delhi",
                "reasoning": "Need more data",
            }),
            self._mock_tool_call("delegate_subagent", {
                "instruction": "Compare the two populations",
                "reasoning": "Need comparison",
            }),
            self._mock_tool_call("finish_task", {
                "answer": "Delhi has a larger population than Tokyo",
                "reasoning": "Comparison complete",
            }),
        ]

        observations = [
            Observation(result_summary="Tokyo: 37 million"),
            Observation(result_summary="Delhi: 32 million"),
            Observation(result_summary="Delhi is larger"),
        ]

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(side_effect=responses)

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(side_effect=observations)
        ):
            result = await orchestrator.run("Which city has more people, Tokyo or Delhi?")

        assert result == "Delhi has a larger population than Tokyo"
        assert orchestrator.state.step == 3
        assert len(orchestrator.state.history) == 3

    @pytest.mark.asyncio
    async def test_max_steps_termination(self, orchestrator):
        """Orchestrator terminates when max_steps reached."""
        # LLM keeps delegating
        delegate_response = self._mock_tool_call("delegate_subagent", {
            "instruction": "More work",
            "reasoning": "Not done yet",
        })

        mock_obs = Observation(result_summary="Done")

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(
                return_value=delegate_response
            )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(return_value=mock_obs)
        ):
            with pytest.raises(RuntimeError, match="max_steps"):
                await orchestrator.run("Keep working")

        assert orchestrator.state.step == 10  # max_steps

    @pytest.mark.asyncio
    async def test_direct_finish_no_delegation(self, orchestrator):
        """LLM decides to finish immediately without delegating."""
        finish_response = self._mock_tool_call("finish_task", {
            "answer": "Paris is the capital of France",
            "reasoning": "Already know this",
        })

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(return_value=finish_response)

        result = await orchestrator.run("What is the capital of France?")

        assert result == "Paris is the capital of France"
        assert orchestrator.state.step == 0
        assert len(orchestrator.state.history) == 0

    @pytest.mark.asyncio
    async def test_delegation_error_doesnt_crash_orchestrator(self, orchestrator):
        """Sub-agent failure is captured, orchestrator continues."""
        # First delegation fails, second succeeds
        delegate_response_1 = self._mock_tool_call("delegate_subagent", {
            "instruction": "Failing task",
            "reasoning": "Test error handling",
        })
        delegate_response_2 = self._mock_tool_call("delegate_subagent", {
            "instruction": "Working task",
            "reasoning": "Retry",
        })
        finish_response = self._mock_tool_call("finish_task", {
            "answer": "Success after error",
            "reasoning": "Recovered",
        })

        # First call raises, second succeeds
        async def mock_create_execute(tuple_def):
            if "Failing" in tuple_def.instruction:
                raise Exception("Simulated failure")
            return Observation(result_summary="Success")

        with patch.object(
            orchestrator.client, "chat", new=MagicMock()
        ):
            orchestrator.client.chat.completions.create = AsyncMock(
                side_effect=[delegate_response_1, delegate_response_2, finish_response]
            )

        with patch.object(
            orchestrator.factory, "create_and_execute", new=AsyncMock(side_effect=mock_create_execute)
        ):
            result = await orchestrator.run("Test error recovery")

        assert result == "Success after error"
        assert orchestrator.state.step == 2
        assert len(orchestrator.state.history) == 2
        # First delegation has error logs
        assert len(orchestrator.state.history[0].observation.error_logs) > 0
        # Second delegation succeeded
        assert orchestrator.state.history[1].observation.result_summary == "Success"

    def _mock_tool_call(self, name: str, arguments: dict) -> MagicMock:
        """Helper to create a mock LLM tool call response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.tool_calls = [
            MagicMock(
                function=MagicMock(
                    name=name,
                    arguments=json.dumps(arguments),
                )
            )
        ]
        return response
```

##### 2. tests/integration/test_with_real_llm.py (optional, new file)

**File**: `tests/integration/test_with_real_llm.py`
**Changes**: Create integration test with real LLM (requires API keys, skipped by default)

```python
"""Integration tests with real LLM.

These tests make actual API calls and require valid credentials.
They are skipped by default. Run with:
    pytest tests/integration/test_with_real_llm.py --integration
"""

import os
import pytest
from aorchestra.core.orchestrator import Orchestrator
from aorchestra.models.config import ModelConfig


pytestmark = pytest.mark.skipif(
    not os.getenv("Z_AI_API_KEY"),
    reason="Requires Z_AI_API_KEY environment variable"
)


class TestRealLLM:
    """Integration tests with real LLM."""

    @pytest.fixture
    def model_config(self):
        """Model config from environment."""
        return ModelConfig(
            name="glm-4-flash",  # Use cheaper model for testing
            api_base="https://api.z.ai/v1",
            api_key=os.getenv("Z_AI_API_KEY", ""),
        )

    @pytest.fixture
    def orchestrator(self, model_config):
        """Orchestrator instance."""
        return Orchestrator(model=model_config, max_steps=5)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_simple_delegation_real_llm(self, orchestrator):
        """Test with real LLM - simple delegation."""
        # Note: This test will actually call the LLM API
        # It requires a working API key and network connection
        result = await orchestrator.run("What is 2 + 2?")

        # The LLM should delegate and produce an answer
        assert result
        assert len(result) > 0
        assert orchestrator.state is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_direct_finish_real_llm(self, orchestrator):
        """Test with real LLM - direct finish."""
        result = await orchestrator.run("What is the capital of France?")

        # The LLM may finish directly without delegating
        assert result
        assert "Paris" in result or "capital" in result.lower()
```

#### Success Criteria:

##### Automated Verification:

- [ ] All tests pass: `pytest tests/ -v -k "orchestrator"`
- [ ] End-to-end tests cover: single delegation, multi-delegation, max_steps, direct finish, error recovery
- [ ] Integration tests marked appropriately (skip without API key)
- [ ] Code coverage: `pytest --cov=aorchestra/orchestrator --cov=aorchestra/core/orchestrator`

##### Manual Verification:

- [ ] Review test coverage comprehensively
- [ ] Verify edge cases are tested
- [ ] Run integration tests manually with real API key (if available)
- [ ] Confirm all success criteria from item.json are met
- [ ] Verify orchestrator never directly executes environment actions

**Note**: Complete all automated verification. Manual verification with real LLM is optional but recommended.

---

## Testing Strategy

### Unit Tests:

**Phase 1 - Models (test_orchestrator_models.py):**
- Model validation (empty fields, negative steps, etc.)
- JSON serialization/deserialization
- State property methods (is_finished)
- Delegation record creation
- Action model creation

**Phase 2 - State Machine (test_orchestrator.py):**
- Orchestrator initialization
- State machine loop execution
- max_steps constraint enforcement
- _delegate() method with mocked factory
- _integrate_observation() state updates
- Stub _decide_action() behavior

**Phase 3 - LLM Decision (test_orchestrator_llm.py):**
- LLM response parsing (Delegate and Finish)
- Function calling integration
- Context building with history
- Prompt construction correctness
- Error handling for malformed LLM responses

**Phase 4 - Delegation (test_orchestrator_delegation.py):**
- Factory integration
- Context building for sub-agents
- Tool filtering (placeholder for item 003)
- Error capture from factory exceptions
- Full workflow with mocked LLM

**Phase 5 - End-to-End (test_orchestrator_e2e.py):**
- Single delegation workflow
- Multi-delegation workflow
- max_steps termination
- Direct finish without delegation
- Error recovery (sub-agent failure doesn't crash)

**Key edge cases:**
- Empty goal string
- Max steps reached without finishing
- LLM returns malformed response
- Factory raises exception
- Sub-agent returns error in Observation
- Very long delegation history

### Integration Tests:

**test_with_real_llm.py (optional):**
- Simple delegation with real LLM
- Direct finish with real LLM
- Multi-step reasoning with real LLM
- Requires Z_AI_API_KEY environment variable
- Marked as skip by default

### Manual Testing Steps:

1. **Verify orchestrator structure:**
   - Confirm Orchestrator class exists in core/orchestrator.py
   - Verify all methods are implemented (run, _decide_action, _delegate, _finish)
   - Check state model tracks history correctly

2. **Test with example goal:**
   ```python
   from aorchestra.core.orchestrator import Orchestrator
   from aorchestra.models.config import ModelConfig

   model = ModelConfig(
       name="glm-4-flash",
       api_base="https://api.z.ai/v1",
       api_key=os.getenv("Z_AI_API_KEY"),
   )

   orchestrator = Orchestrator(model=model, max_steps=5)
   result = await orchestrator.run("What is the capital of France?")
   print(result)
   ```

3. **Verify state history:**
   ```python
   print(f"Steps: {orchestrator.state.step}")
   print(f"Delegations: {len(orchestrator.state.history)}")
   for d in orchestrator.state.history:
       print(f"  - {d.tuple.instruction}: {d.observation.result_summary}")
   ```

4. **Test max_steps constraint:**
   ```python
   orchestrator = Orchestrator(model=model, max_steps=2)
   try:
       result = await orchestrator.run("Complex multi-step task")
   except RuntimeError as e:
       assert "max_steps" in str(e)
   ```

5. **Verify error handling:**
   - Force sub-agent failure and confirm orchestrator continues
   - Check error logs are captured in Observation

## Migration Notes

No migration needed - this is new functionality. Item 001 remains unchanged.

## References

- Research: `C:\Users\strau\clawd\aorchestra\.wreckit\items\002-orchestrator-delegate-finish\research.md`
- Item 001 Foundation:
  - `aorchestra/core/tuples.py` - AgentTuple dataclass
  - `aorchestra/core/factory.py` - AgentFactory.create_and_execute()
  - `aorchestra/core/observations.py` - Observation model
  - `aorchestra/models/config.py` - ModelConfig
- Testing patterns: `C:\Users\strau\clawd\aorchestra\tests\test_factory.py`
- Item definition: `C:\Users\strau\clawd\aorchestra\.wreckit\items\002-orchestrator-delegate-finish\item.json`
