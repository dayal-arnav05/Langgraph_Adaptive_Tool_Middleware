"""
LangGraph Integration Example

Shows how to mount the production middleware over LangGraph tool execution.
"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated, TypedDict

# Add parent to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from src.production_middleware import ProductionToolMiddleware
from src.tools import get_tools_for_llm


# Define state
class AgentState(TypedDict):
    messages: list


# Create tools
tools = get_tools_for_llm()


# Initialize middleware
middleware = ProductionToolMiddleware(
    enable_circuit_breaker=True,
    enable_error_feedback=True,
    enable_observability=True,
    max_retries=3
)


def create_resilient_tool_node(tools_list):
    """
    Create a tool node that uses our production middleware for execution.
    
    This wraps LangGraph's tool execution with retry, circuit breakers,
    and error recovery.
    """
    
    async def execute_tools(state: AgentState) -> dict:
        """Execute tools with production middleware"""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Get tool calls from last AI message
        tool_calls = getattr(last_message, "tool_calls", [])
        
        if not tool_calls:
            return {"messages": []}
        
        # Execute each tool call with middleware
        tool_messages = []
        
        for tool_call in tool_calls:
            print(f"\n🔧 Executing tool: {tool_call['name']}")
            
            # Use middleware for resilient execution
            result = await middleware.execute(
                tool_call=tool_call,
                user_query=messages[0].content if messages else ""
            )
            
            # Create tool message for LangGraph
            if result["success"]:
                content = result["result"]
                print(f"✅ Success (attempts: {result['metadata']['attempts']})")
            else:
                content = f"Error: {result['error']}"
                print(f"❌ Failed after {result['metadata']['attempts']} attempts")
            
            tool_message = ToolMessage(
                content=str(content),
                tool_call_id=tool_call["id"],
                name=tool_call["name"]
            )
            tool_messages.append(tool_message)
        
        return {"messages": tool_messages}
    
    return execute_tools


def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If there are tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end
    return END


async def call_model(state: AgentState) -> dict:
    """Call the LLM"""
    messages = state["messages"]
    
    # Initialize model with tools
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    model_with_tools = model.bind_tools(tools)
    
    response = await model_with_tools.ainvoke(messages)
    
    return {"messages": [response]}


def create_agent_graph():
    """
    Create LangGraph agent with production middleware.
    
    This demonstrates how to integrate the middleware into your
    LangGraph workflows for production-ready tool execution.
    """
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", create_resilient_tool_node(tools))
    
    # Add edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


async def run_example():
    """Run example queries through the agent"""
    
    print("\n" + "="*80)
    print("LangGraph + Production Middleware Integration")
    print("="*80)
    print("\nThis demonstrates resilient tool execution in LangGraph:")
    print("  ✓ Automatic retry on failures")
    print("  ✓ Circuit breakers for unhealthy tools")
    print("  ✓ Error feedback for LLM correction")
    print("  ✓ Full observability")
    print("\n" + "="*80 + "\n")
    
    # Create agent
    agent = create_agent_graph()
    
    # Example queries
    queries = [
        "What's the weather in London?",
        "Search for recent AI news",
        "Calculate 25 * 4 + 10",
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'─'*80}")
        print(f"Query {i}: {query}")
        print(f"{'─'*80}")
        
        # Run agent
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        
        # Print final response
        final_message = result["messages"][-1]
        print(f"\n💬 Response: {final_message.content}\n")
    
    # Print middleware statistics
    print("\n" + "="*80)
    print("Middleware Statistics")
    print("="*80)
    middleware.print_stats()
    print()


async def run_with_simulated_failures():
    """
    Run example with simulated failures to show middleware in action.
    
    This demonstrates how the middleware handles real production issues.
    """
    
    print("\n" + "="*80)
    print("DEMO: Middleware Handling Simulated Failures")
    print("="*80)
    print("\nSimulating network issues, rate limits, and API errors...")
    print("Watch how the middleware recovers from failures!\n")
    
    # Simulate a query that would fail without middleware
    agent = create_agent_graph()
    
    query = "What's the weather in Tokyo and search for climate change news?"
    
    print(f"Query: {query}\n")
    
    result = await agent.ainvoke({
        "messages": [HumanMessage(content=query)]
    })
    
    print(f"\n✅ Successfully handled query despite potential failures!")
    print(f"Final response: {result['messages'][-1].content}\n")
    
    middleware.print_stats()


if __name__ == "__main__":
    import os
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  Set OPENAI_API_KEY in .env file first!")
        print("   Example: OPENAI_API_KEY=sk-...\n")
        sys.exit(1)
    
    print("\n🎯 Choose demo:")
    print("   1. Normal operation (real LLM calls)")
    print("   2. Simulated failures (shows recovery)")
    
    choice = input("\nChoice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(run_with_simulated_failures())
    else:
        asyncio.run(run_example())

