"""
LangGraph Quickstart - 3 Lines to Production-Ready Tool Execution

This example shows how simple it is to add production resilience
to your LangGraph agents.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Annotated, TypedDict
from operator import add

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from src.production_middleware import ProductionToolMiddleware
from src.langgraph_integration import create_resilient_tool_node, AgentState
from src.tools import get_tools_for_llm


def should_continue(state: AgentState) -> str:
    """Routing function"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


async def call_model(state: AgentState) -> dict:
    """Call LLM with tools"""
    messages = state["messages"]
    tools = get_tools_for_llm()
    
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    model_with_tools = model.bind_tools(tools)
    
    response = await model_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def main():
    """
    Complete LangGraph agent with production middleware in just 3 lines!
    """
    
    print("\n" + "="*80)
    print("LangGraph Quickstart - Production Tool Execution in 3 Lines")
    print("="*80)
    print()
    
    # ========================================================================
    # STEP 1: Initialize middleware (1 line)
    # ========================================================================
    middleware = ProductionToolMiddleware(
        enable_circuit_breaker=True,
        enable_error_feedback=False,  # Set True to enable LLM correction
        max_retries=3
    )
    print("✅ Step 1: Middleware initialized")
    
    # ========================================================================
    # STEP 2: Create your graph as normal (standard LangGraph code)
    # ========================================================================
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    print("✅ Step 2: Graph created")
    
    # ========================================================================
    # STEP 3: Use resilient tool node instead of regular ToolNode (1 line!)
    # ========================================================================
    workflow.add_node("tools", create_resilient_tool_node(middleware))
    print("✅ Step 3: Resilient tools added")
    
    # Add edges (standard LangGraph)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    
    # Compile
    agent = workflow.compile()
    
    print("\n" + "="*80)
    print("Agent Ready - Now with automatic retry, circuit breakers, and recovery!")
    print("="*80 + "\n")
    
    # Test queries
    queries = [
        "What's 25 times 4 plus 10?",
        "What's the weather in Tokyo?",
    ]
    
    for query in queries:
        print(f"\n{'─'*80}")
        print(f"Query: {query}")
        print(f"{'─'*80}")
        
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        
        final_message = result["messages"][-1]
        print(f"Response: {final_message.content}")
    
    # Show stats
    print("\n" + "="*80)
    print("Middleware Statistics")
    print("="*80)
    middleware.print_stats()
    
    print("\n" + "="*80)
    print("That's it! Just 3 lines to add production resilience:")
    print("="*80)
    print("""
    1. middleware = ProductionToolMiddleware()
    2. workflow.add_node("agent", call_model)
    3. workflow.add_node("tools", create_resilient_tool_node(middleware))
    
    Your tools now have:
    ✓ Automatic retry on failures
    ✓ Circuit breakers for unhealthy tools
    ✓ Error recovery
    ✓ Full observability
    """)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  Set OPENAI_API_KEY in .env file first!")
        print("   Example: OPENAI_API_KEY=sk-...\n")
        sys.exit(1)
    
    asyncio.run(main())

