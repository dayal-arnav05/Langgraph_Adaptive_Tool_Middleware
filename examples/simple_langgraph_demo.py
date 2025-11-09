"""
Simple LangGraph + Middleware Demo

Shows the middleware working without complex graph flows.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.production_middleware import ProductionToolMiddleware


async def demo():
    """Simple demo showing middleware in action"""
    
    print("\n" + "="*80)
    print("LangGraph Production Middleware Demo")
    print("="*80)
    print("\nThis shows how the middleware wraps tool execution for LangGraph.\n")
    
    # Initialize middleware
    middleware = ProductionToolMiddleware(
        enable_circuit_breaker=True,
        enable_error_feedback=False,  # Disable to avoid API calls
        enable_observability=True,
        max_retries=3
    )
    
    # Simulate tool calls that would come from LangGraph
    tool_calls = [
        {
            "name": "get_weather",
            "id": "call_1",
            "arguments": {"location": "London", "country": "GB"}
        },
        {
            "name": "calculator",
            "id": "call_2",
            "arguments": {"expression": "25 * 4 + 10"}
        },
        {
            "name": "search_web",
            "id": "call_3",
            "arguments": {"query": "latest AI news", "num_results": 5}
        }
    ]
    
    print("Executing 3 tool calls with middleware...\n")
    
    for i, tool_call in enumerate(tool_calls, 1):
        print(f"{'─'*80}")
        print(f"Tool Call #{i}")
        print(f"{'─'*80}")
        print(f"Tool: {tool_call['name']}")
        print(f"Args: {tool_call['arguments']}")
        
        # Execute with middleware (this is what LangGraph would do)
        result = await middleware.execute(
            tool_call=tool_call,
            user_query=f"Execute {tool_call['name']}"
        )
        
        if result["success"]:
            print(f"\n✅ SUCCESS")
            print(f"   Attempts: {result['metadata']['attempts']}")
            print(f"   Duration: {result['metadata']['duration']:.3f}s")
            print(f"   Result: {str(result['result'])[:100]}...")
        else:
            print(f"\n❌ FAILED")
            print(f"   Error: {result['error']}")
            print(f"   Attempts: {result['metadata']['attempts']}")
        
        print()
    
    # Show statistics
    print("="*80)
    print("Middleware Statistics")
    print("="*80)
    middleware.print_stats()
    
    print("\n" + "="*80)
    print("Integration Pattern for LangGraph")
    print("="*80)
    print("""
In your LangGraph workflow, replace tool execution with:

async def execute_tools(state):
    tool_calls = state["messages"][-1].tool_calls
    
    tool_messages = []
    for tool_call in tool_calls:
        # Use middleware for resilient execution
        result = await middleware.execute(
            tool_call=tool_call,
            user_query=state["messages"][0].content
        )
        
        # Convert to LangGraph ToolMessage
        tool_messages.append(ToolMessage(
            content=result["result"] if result["success"] else result["error"],
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": tool_messages}

workflow.add_node("tools", execute_tools)
""")


if __name__ == "__main__":
    asyncio.run(demo())

