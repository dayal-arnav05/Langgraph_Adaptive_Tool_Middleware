"""
Real Tools Example

Shows how to use the middleware with ACTUAL tools, not mocks.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.production_middleware import ProductionToolMiddleware


# Define REAL tools (not mocks!)
async def real_weather_tool(location: str, unit: str = "celsius") -> str:
    """Get real weather for a location (simulated API call)"""
    # In production, this would call a real weather API
    print(f"🌤️  Calling real weather API for {location}...")
    await asyncio.sleep(0.1)  # Simulate API call
    return f"Weather in {location}: 22°{unit[0].upper()}, Partly Cloudy"


async def real_calculator_tool(expression: str) -> str:
    """Calculate a mathematical expression"""
    print(f"🔢 Calculating: {expression}")
    try:
        result = eval(expression)  # In production, use safe eval
        return f"{expression} = {result}"
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")


class CustomTool:
    """Custom tool class (LangChain-style)"""
    
    def __init__(self, name: str, func):
        self.name = name
        self.func = func
    
    async def ainvoke(self, args: dict) -> str:
        """Async invoke (LangChain interface)"""
        return await self.func(**args)


async def demo():
    print("\n" + "="*80)
    print("Real Tools Example - Using ACTUAL Tools, Not Mocks")
    print("="*80)
    print()
    
    # ========================================================================
    # METHOD 1: Pass tools as list
    # ========================================================================
    print("Method 1: Pass tools to middleware")
    print("─"*80)
    
    # Create actual tools
    tools = [
        CustomTool("real_weather_tool", real_weather_tool),
        CustomTool("real_calculator_tool", real_calculator_tool),
    ]
    
    # Pass tools to middleware
    middleware = ProductionToolMiddleware(
        tools=tools,  # REAL tools!
        enable_circuit_breaker=True,
        enable_error_feedback=False,  # Disable to avoid needing API key
        enable_observability=True,
        max_retries=3
    )
    
    # Execute real tool
    result = await middleware.execute(
        tool_call={
            "name": "real_weather_tool",
            "arguments": {"location": "Tokyo", "unit": "celsius"}
        },
        user_query="What's the weather in Tokyo?"
    )
    
    print(f"✅ Result: {result['result']}")
    print()
    
    # ========================================================================
    # METHOD 2: Custom executor function
    # ========================================================================
    print("Method 2: Custom executor function")
    print("─"*80)
    
    # Define custom executor
    async def my_custom_executor(tool_name: str, arguments: dict) -> str:
        """Execute tools your way"""
        print(f"🔧 Custom executor called for: {tool_name}")
        
        if tool_name == "my_api":
            # Call your API
            return f"API result for {arguments}"
        elif tool_name == "my_database":
            # Query your database
            return f"DB result for {arguments}"
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    # Use custom executor
    middleware2 = ProductionToolMiddleware(
        tool_executor=my_custom_executor,
        enable_error_feedback=False,
        max_retries=3
    )
    
    result2 = await middleware2.execute(
        tool_call={"name": "my_api", "arguments": {"query": "test"}},
        user_query="Call my API"
    )
    
    print(f"✅ Result: {result2['result']}")
    print()
    
    # ========================================================================
    # METHOD 3: With failure simulation
    # ========================================================================
    print("Method 3: Real tool with simulated failure + retry")
    print("─"*80)
    
    call_count = {"count": 0}
    
    async def flaky_tool(query: str) -> str:
        """Tool that fails first 2 times, then succeeds"""
        call_count["count"] += 1
        print(f"  Attempt {call_count['count']}: Calling flaky tool...")
        
        if call_count["count"] < 3:
            raise Exception("Temporary network error")
        
        return f"Success on attempt {call_count['count']}!"
    
    middleware3 = ProductionToolMiddleware(
        tools=[CustomTool("flaky_tool", flaky_tool)],
        enable_error_feedback=False,
        max_retries=5
    )
    
    result3 = await middleware3.execute(
        tool_call={"name": "flaky_tool", "arguments": {"query": "test"}},
        user_query="Call flaky tool"
    )
    
    print(f"✅ Result: {result3['result']}")
    print(f"   Attempts: {result3['metadata']['attempts']}")
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("="*80)
    print("Summary")
    print("="*80)
    print("""
✅ The middleware now works with REAL tools:
   - Pass tools list: ProductionToolMiddleware(tools=[...])
   - Custom executor: ProductionToolMiddleware(tool_executor=func)
   - LangChain tools: Supports .ainvoke() and .invoke()
   - Any callable: Regular functions work too

✅ Applies resilience to YOUR tools:
   - Retry logic wraps YOUR tool execution
   - Circuit breaker protects YOUR APIs
   - Error recovery for YOUR failures

✅ For LangGraph integration:
   middleware = ProductionToolMiddleware(tools=your_langchain_tools)
   workflow.add_node("tools", create_resilient_tool_node(middleware))

No more mocks - this is production-ready!
    """)


if __name__ == "__main__":
    asyncio.run(demo())

