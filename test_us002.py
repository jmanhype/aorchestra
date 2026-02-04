"""Test US-002 and US-003 acceptance criteria"""

from aorchestra.tools import ToolRegistry, ToolMetadata
from aorchestra.tools.mock import CalculatorTool

# Test US-002: ToolRegistry core operations
print("=" * 60)
print("Testing US-002: ToolRegistry class with core operations")
print("=" * 60)

# Test ToolRegistry can be instantiated without arguments
print("\nTest 1: Instantiation")
registry = ToolRegistry()
print("  [OK] Registry created successfully")

# Test register validates tool implements Tool protocol
print("\nTest 2: Tool validation")
calc = CalculatorTool()
meta = ToolMetadata(
    name='calculator',
    description=calc.description,
    tags=['math'],
    capabilities=['add', 'subtract']
)
registry.register(calc, meta)
print("  [OK] Tool registered successfully")

# Test register validates tool.name == metadata.name
print("\nTest 3: Name mismatch validation")
try:
    bad_meta = ToolMetadata(name='wrong_name', description='desc')
    registry.register(calc, bad_meta)
    print("  [FAIL] ERROR: Should have raised ValueError")
except ValueError:
    print("  [OK] Correctly raised ValueError for name mismatch")

# Test register raises ValueError for duplicate tool names
print("\nTest 4: Duplicate detection")
try:
    registry.register(calc, meta)
    print("  [FAIL] ERROR: Should have raised ValueError")
except ValueError:
    print("  [OK] Correctly raised ValueError for duplicate name")

# Test get(name) returns tool or None
print("\nTest 5: get() method")
tool = registry.get('calculator')
assert tool is calc
print("  [OK] get('calculator') returns the tool")
tool = registry.get('nonexistent')
assert tool is None
print("  [OK] get('nonexistent') returns None")

# Test get_metadata(name) returns metadata or None
print("\nTest 6: get_metadata() method")
metadata = registry.get_metadata('calculator')
assert metadata.name == 'calculator'
print("  [OK] get_metadata('calculator') returns metadata")
metadata = registry.get_metadata('nonexistent')
assert metadata is None
print("  [OK] get_metadata('nonexistent') returns None")

# Test get_all() returns list of all registered tools
print("\nTest 7: get_all() method")
all_tools = registry.get_all()
assert len(all_tools) == 1
print("  [OK] get_all() returns correct number of tools")

# Test list_tools() returns list of all tool names
print("\nTest 8: list_tools() method")
names = registry.list_tools()
assert names == ['calculator']
print("  [OK] list_tools() returns correct tool names")

# Test unregister(name) removes tool and raises KeyError if not found
print("\nTest 9: unregister() method")
registry.unregister('calculator')
assert 'calculator' not in registry
print("  [OK] unregister('calculator') removes the tool")
try:
    registry.unregister('nonexistent')
    print("  [FAIL] ERROR: Should have raised KeyError")
except KeyError:
    print("  [OK] unregister('nonexistent') raises KeyError")

# Test __len__() returns number of registered tools
print("\nTest 10: __len__() method")
registry2 = ToolRegistry()
assert len(registry2) == 0
print("  [OK] Empty registry length is 0")
registry2.register(calc, meta)
assert len(registry2) == 1
print("  [OK] Registry with 1 tool length is 1")

# Test __contains__(name) checks if tool is registered
print("\nTest 11: __contains__() method")
assert 'calculator' in registry2
print("  [OK] 'calculator' in registry returns True")
assert 'nonexistent' not in registry2
print("  [OK] 'nonexistent' in registry returns False")

# Test US-003: ToolRegistry.select_tools() with filtering logic
print("\n" + "=" * 60)
print("Testing US-003: ToolRegistry.select_tools() with filtering logic")
print("=" * 60)

# Register multiple tools for testing
from aorchestra.tools import ToolSelectionCriteria
registry3 = ToolRegistry()

# Register calculator
calc_meta = ToolMetadata(
    name='calculator',
    description='Performs arithmetic operations',
    tags=['math', 'calculation'],
    capabilities=['add', 'subtract', 'multiply', 'divide']
)
registry3.register(CalculatorTool(), calc_meta)

# Register a custom file tool
class FileTool:
    name = 'file_read'
    description = 'Reads file contents'
    async def execute(self, **kwargs):
        return "content"

file_meta = ToolMetadata(
    name='file_read',
    description='Reads file contents from disk',
    tags=['file', 'io'],
    capabilities=['read', 'filesystem']
)
registry3.register(FileTool(), file_meta)

# Test: If tool_names specified, returns only those tools
print("\nTest 12: Select by tool_names")
tools = registry3.select_tools(
    ToolSelectionCriteria(tool_names=['calculator'])
)
assert len(tools) == 1
assert tools[0].name == 'calculator'
print("  [OK] Select by tool_names returns correct tools")

# Test: If tags specified, matches tools with any of the tags
print("\nTest 13: Select by tags")
tools = registry3.select_tools(
    ToolSelectionCriteria(tags=['math'])
)
assert len(tools) == 1
assert tools[0].name == 'calculator'
print("  [OK] Select by tags (OR logic) works")

tools = registry3.select_tools(
    ToolSelectionCriteria(tags=['file', 'math'])
)
assert len(tools) == 2
print("  [OK] Select by multiple tags matches tools with any tag")

# Test: If capabilities specified, matches tools with any capabilities
print("\nTest 14: Select by capabilities")
tools = registry3.select_tools(
    ToolSelectionCriteria(capabilities=['add'])
)
assert len(tools) == 1
assert tools[0].name == 'calculator'
print("  [OK] Select by capabilities (OR logic) works")

# Test: If keywords specified, matches tools with keywords in description
print("\nTest 15: Select by keywords")
tools = registry3.select_tools(
    ToolSelectionCriteria(keywords=['arithmetic'])
)
assert len(tools) == 1
assert tools[0].name == 'calculator'
print("  [OK] Select by keywords (case-insensitive) works")

tools = registry3.select_tools(
    ToolSelectionCriteria(keywords=['FILE'])
)
assert len(tools) == 1
assert tools[0].name == 'file_read'
print("  [OK] Keyword matching is case-insensitive")

# Test: Respects max_tools limit
print("\nTest 16: max_tools limit")
tools = registry3.select_tools(
    ToolSelectionCriteria(tags=['file', 'math'], max_tools=1)
)
assert len(tools) == 1
print("  [OK] max_tools limit is respected")

# Test: Returns empty list if no tools match criteria
print("\nTest 17: No matches returns empty list")
tools = registry3.select_tools(
    ToolSelectionCriteria(tags=['nonexistent_tag'])
)
assert len(tools) == 0
print("  [OK] Returns empty list when no tools match")

# Test: All filters can be used together
print("\nTest 18: Combined filters")
tools = registry3.select_tools(
    ToolSelectionCriteria(
        tags=['math'],
        capabilities=['add'],
        keywords=['arithmetic']
    )
)
assert len(tools) == 1
assert tools[0].name == 'calculator'
print("  [OK] Combined filters work (AND logic between filter groups)")

print("\n" + "=" * 60)
print("All US-002 and US-003 tests passed!")
print("=" * 60)
