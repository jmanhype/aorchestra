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
