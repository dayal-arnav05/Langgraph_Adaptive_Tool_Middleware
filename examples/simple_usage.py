"""
Simple Usage Example

Basic example showing how to use the middleware without LangGraph.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.production_middleware import ProductionToolMiddleware


async def main():
    """Simple usage example"""
    
    print("\n" + "="*70)
    print("Simple Middleware Usage Example")
    print("="*70 + "\n")
    
    # Initialize middleware
    middleware = ProductionToolMiddleware(
        enable_circuit_breaker=True,
        enable_error_feedback=False,  # Set True to use LLM correction
        enable_observability=True,
        max_retries=3
    )
    
    # Example tool calls
    tool_calls = [
        {
            "name": "get_weather",
            "arguments": {"location": "San Francisco", "country": "US"}
        },
        {
            "name": "calculator",
            "arguments": {"expression": "15 * 8"}
        },
        {
            "name": "search_web",
            "arguments": {"query": "latest tech news", "num_results": 5}
        }
    ]
    
    # Execute each tool
    for i, tool_call in enumerate(tool_calls, 1):
        print(f"\nTest {i}: {tool_call['name']}")
        print(f"{'─'*70}")
        
        result = await middleware.execute(
            tool_call=tool_call,
            user_query=f"Execute {tool_call['name']}"
        )
        
        if result["success"]:
            print(f"✅ Success!")
            print(f"   Result: {result['result']}")
            print(f"   Attempts: {result['metadata']['attempts']}")
            print(f"   Duration: {result['metadata']['duration']:.3f}s")
        else:
            print(f"❌ Failed!")
            print(f"   Error: {result['error']}")
            print(f"   Attempts: {result['metadata']['attempts']}")
    
    # Print statistics
    print(f"\n{'='*70}")
    print("Statistics")
    print(f"{'='*70}")
    middleware.print_stats()


if __name__ == "__main__":
    asyncio.run(main())

