"""Core agent abstraction module."""

from aorchestra.core.tuples import AgentTuple
from aorchestra.core.observations import Observation
from aorchestra.core.agents import SubAgent
from aorchestra.core.factory import AgentFactory

# Orchestrator imported lazily to avoid circular import with aorchestra.orchestrator
# Use: from aorchestra.core.orchestrator import Orchestrator
def __getattr__(name):
    if name == "Orchestrator":
        from aorchestra.core.orchestrator import Orchestrator
        return Orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AgentTuple",
    "Observation",
    "SubAgent",
    "AgentFactory",
    "Orchestrator",
]
