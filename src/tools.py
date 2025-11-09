"""
Sample Tool Definitions for Testing

Defines a set of sample tools with clear schemas for testing HiTEC framework.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json


class ToolParameter(BaseModel):
    """Schema for a tool parameter"""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    format: Optional[str] = None


class ToolDefinition(BaseModel):
    """Schema for a complete tool definition"""
    name: str
    description: str
    parameters: List[ToolParameter]
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                param_schema["enum"] = param.enum
            if param.format:
                param_schema["format"] = param.format
            
            properties[param.name] = param_schema
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


# Define sample tools
SAMPLE_TOOLS = [
    ToolDefinition(
        name="get_weather",
        description="Get current weather information for a specific location",
        parameters=[
            ToolParameter(
                name="location",
                type="string",
                description="City name or city with country code (e.g., 'London' or 'London,UK')",
                required=True
            ),
            ToolParameter(
                name="units",
                type="string",
                description="Temperature units",
                required=False,
                enum=["celsius", "fahrenheit", "kelvin"]
            )
        ]
    ),
    ToolDefinition(
        name="search_web",
        description="Search the web for information",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="Search query string (should be specific and descriptive)",
                required=True
            ),
            ToolParameter(
                name="num_results",
                type="integer",
                description="Number of results to return (1-10)",
                required=False
            )
        ]
    ),
    ToolDefinition(
        name="calculator",
        description="Perform mathematical calculations",
        parameters=[
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')",
                required=True
            )
        ]
    ),
    ToolDefinition(
        name="get_stock_price",
        description="Get current stock price for a company",
        parameters=[
            ToolParameter(
                name="ticker",
                type="string",
                description="Stock ticker symbol (e.g., 'AAPL', 'GOOGL')",
                required=True
            ),
            ToolParameter(
                name="exchange",
                type="string",
                description="Stock exchange",
                required=False,
                enum=["NYSE", "NASDAQ", "LSE", "TSE"]
            )
        ]
    ),
    ToolDefinition(
        name="book_restaurant",
        description="Book a table at a restaurant",
        parameters=[
            ToolParameter(
                name="restaurant_name",
                type="string",
                description="Name of the restaurant",
                required=True
            ),
            ToolParameter(
                name="date",
                type="string",
                description="Reservation date in YYYY-MM-DD format",
                required=True,
                format="date"
            ),
            ToolParameter(
                name="time",
                type="string",
                description="Reservation time in HH:MM format (24-hour)",
                required=True,
                format="time"
            ),
            ToolParameter(
                name="party_size",
                type="integer",
                description="Number of people (1-20)",
                required=True
            )
        ]
    ),
    ToolDefinition(
        name="send_email",
        description="Send an email to a recipient",
        parameters=[
            ToolParameter(
                name="to",
                type="string",
                description="Recipient email address",
                required=True,
                format="email"
            ),
            ToolParameter(
                name="subject",
                type="string",
                description="Email subject line",
                required=True
            ),
            ToolParameter(
                name="body",
                type="string",
                description="Email body content",
                required=True
            ),
            ToolParameter(
                name="priority",
                type="string",
                description="Email priority level",
                required=False,
                enum=["low", "normal", "high"]
            )
        ]
    ),
]


def get_tools_for_llm() -> List[Dict[str, Any]]:
    """Get all tools in OpenAI function calling format"""
    return [tool.to_function_schema() for tool in SAMPLE_TOOLS]


def get_tool_by_name(name: str) -> Optional[ToolDefinition]:
    """Get tool definition by name"""
    for tool in SAMPLE_TOOLS:
        if tool.name == name:
            return tool
    return None


# Mock tool execution (for testing purposes)
def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock execution of a tool. Returns success/failure based on parameter validation.
    In a real system, this would actually call the tool.
    """
    tool = get_tool_by_name(tool_name)
    if not tool:
        return {"success": False, "error": f"Tool {tool_name} not found"}
    
    # Validate parameters
    errors = []
    
    # Check required parameters
    required_params = [p.name for p in tool.parameters if p.required]
    for req_param in required_params:
        if req_param not in arguments or arguments[req_param] is None or arguments[req_param] == "":
            errors.append(f"Missing required parameter: {req_param}")
    
    # Check for hallucinated parameters
    valid_params = [p.name for p in tool.parameters]
    for arg_name in arguments.keys():
        if arg_name not in valid_params:
            errors.append(f"Invalid parameter: {arg_name} (not in tool schema)")
    
    # Check enum constraints
    for param in tool.parameters:
        if param.enum and param.name in arguments:
            if arguments[param.name] not in param.enum:
                errors.append(f"Invalid value for {param.name}: {arguments[param.name]}. Must be one of {param.enum}")
    
    # Check type constraints (basic)
    for param in tool.parameters:
        if param.name in arguments and arguments[param.name] is not None:
            value = arguments[param.name]
            if param.type == "integer" and not isinstance(value, int):
                try:
                    int(value)
                except:
                    errors.append(f"Parameter {param.name} must be an integer, got {type(value).__name__}")
    
    if errors:
        return {
            "success": False,
            "errors": errors,
            "tool": tool_name,
            "arguments": arguments
        }
    
    # Mock successful execution
    return {
        "success": True,
        "tool": tool_name,
        "arguments": arguments,
        "result": f"Successfully executed {tool_name} with arguments: {json.dumps(arguments)}"
    }

