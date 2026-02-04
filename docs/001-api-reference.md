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
