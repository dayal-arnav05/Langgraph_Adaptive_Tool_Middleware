"""
Native LangGraph Integration

Provides drop-in replacement for LangGraph's ToolNode with production resilience.
"""

from typing import Dict, Any, List, Optional, TypedDict, Annotated
from operator import add
import warnings

try:
    from langchain_core.messages import ToolMessage, BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    warnings.warn(
        "langchain-core not installed. LangGraph integration will not work. "
        "Install with: pip install langchain-core"
    )


class AgentState(TypedDict):
    """Standard LangGraph agent state."""
    messages: Annotated[list, add]


def create_resilient_tool_node(middleware, tools=None):
    """
    Drop-in replacement for LangGraph's ToolNode with production resilience.
    
    Provides automatic retry, circuit breakers, and error recovery for tool execution.
    
    Usage:
        from src.production_middleware import ProductionToolMiddleware
        from src.langgraph_integration import create_resilient_tool_node
        
        # Option 1: Pass tools to middleware (RECOMMENDED)
        tools = [your_weather_tool, your_search_tool, ...]
        middleware = ProductionToolMiddleware(
            tools=tools,  # Your actual tools!
            enable_circuit_breaker=True,
            max_retries=3
        )
        workflow.add_node("tools", create_resilient_tool_node(middleware))
        
        # Option 2: Pass tools to this function
        middleware = ProductionToolMiddleware(max_retries=3)
        workflow.add_node("tools", create_resilient_tool_node(middleware, tools=tools))
        
        # Option 3: Custom executor
        async def my_executor(tool_name, args):
            # Your custom tool execution logic
            return result
        
        middleware = ProductionToolMiddleware(tool_executor=my_executor)
        workflow.add_node("tools", create_resilient_tool_node(middleware))
    
    Args:
        middleware: ProductionToolMiddleware instance
        tools: Optional list of actual tools to execute
    
    Returns:
        Async function compatible with LangGraph's add_node()
    """
    
    # If tools provided here, add them to middleware
    if tools and not middleware.tools:
        middleware.tools = tools
        middleware._tool_map = {}
        for tool in tools:
            tool_name = getattr(tool, 'name', None) or getattr(tool, '__name__', str(tool))
            middleware._tool_map[tool_name] = tool
    
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            "langchain-core is required for LangGraph integration. "
            "Install with: pip install langchain-core"
        )
    
    async def execute_tools(state: AgentState) -> dict:
        """
        Execute tools with production middleware.
        
        This function handles:
        - Format conversion (LangChain 'args' -> middleware 'arguments')
        - Result extraction and cleaning
        - Error handling and retry
        - Circuit breaking
        - Observability
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # Get tool calls from last AI message
        tool_calls = getattr(last_message, "tool_calls", [])
        
        if not tool_calls:
            return {"messages": []}
        
        # Execute each tool call with middleware
        tool_messages = []
        
        for tool_call in tool_calls:
            # Use the new LangGraph-aware method
            result = await middleware.execute_langchain_tool(
                tool_call=tool_call,
                user_query=messages[0].content if messages else ""
            )
            
            # Create LangGraph-compatible tool message
            tool_message = ToolMessage(
                content=result["content"],
                tool_call_id=tool_call["id"],
                name=tool_call.get("name", "unknown")
            )
            tool_messages.append(tool_message)
        
        return {"messages": tool_messages}
    
    return execute_tools


def create_resilient_tool_node_with_fallback(middleware, fallback_response="Tool execution failed."):
    """
    Create resilient tool node with custom fallback response.
    
    If tool execution fails after all retries, returns a custom message
    instead of the raw error.
    
    Usage:
        workflow.add_node(
            "tools", 
            create_resilient_tool_node_with_fallback(
                middleware,
                fallback_response="I encountered an error. Please try again."
            )
        )
    """
    
    async def execute_tools(state: AgentState) -> dict:
        messages = state["messages"]
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        
        if not tool_calls:
            return {"messages": []}
        
        tool_messages = []
        
        for tool_call in tool_calls:
            result = await middleware.execute_langchain_tool(
                tool_call=tool_call,
                user_query=messages[0].content if messages else ""
            )
            
            # Use fallback for failures
            content = result["content"] if result["success"] else fallback_response
            
            tool_message = ToolMessage(
                content=content,
                tool_call_id=tool_call["id"],
                name=tool_call.get("name", "unknown")
            )
            tool_messages.append(tool_message)
        
        return {"messages": tool_messages}
    
    return execute_tools

