"""
Error Feedback Loop

Feeds REAL execution errors back to LLM for correction.
This is the key insight - don't predict errors, learn from actual failures.
"""

from typing import Dict, Any, List, Optional
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    PROJECT_ROOT = Path(__file__).parent.parent
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    # .env loading failed, continue without it
    pass


class ErrorFeedbackLoop:
    """
    Feeds real execution errors back to LLM for correction.
    
    Key insight: REAL errors are more informative than predicted ones.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        max_correction_attempts: int = 2
    ):
        self.model = model
        self.provider = provider.lower()
        self.max_correction_attempts = max_correction_attempts
        
        # Initialize LLM client
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Track corrections
        self.correction_history = []
    
    async def generate_correction(
        self,
        original_call: Dict[str, Any],
        error_message: str,
        error_type: str,
        user_query: str,
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate corrected tool call based on REAL error.
        
        Args:
            original_call: The tool call that failed
            error_message: Actual error from tool execution
            error_type: Type of error (timeout, rate_limit, tool_error, etc.)
            user_query: Original user request
            available_tools: Available tools
            context: Additional context
        
        Returns:
            Corrected tool call
        """
        correction_prompt = self._build_correction_prompt(
            original_call,
            error_message,
            error_type,
            user_query,
            context
        )
        
        # Generate correction
        if self.provider == "openai":
            corrected = await self._generate_openai(correction_prompt, available_tools)
        else:
            corrected = await self._generate_anthropic(correction_prompt, available_tools)
        
        # Record correction
        self.correction_history.append({
            "original": original_call,
            "error": error_message,
            "error_type": error_type,
            "corrected": corrected,
            "user_query": user_query
        })
        
        return corrected
    
    def _build_correction_prompt(
        self,
        original_call: Dict[str, Any],
        error_message: str,
        error_type: str,
        user_query: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for correction"""
        
        prompt = f"""The previous tool call failed with an error. Please generate a corrected version.

USER QUERY: {user_query}

FAILED TOOL CALL:
Tool: {original_call.get('name', 'unknown')}
Arguments: {json.dumps(original_call.get('arguments', {}), indent=2)}

ERROR RECEIVED:
{error_message}

ERROR TYPE: {error_type}

"""
        
        # Add specific guidance based on error type
        if error_type == "rate_limit":
            prompt += """
GUIDANCE: The API rate limit was exceeded. Consider:
- Using a different tool if available
- Reducing the scope of the request
- Checking if arguments are too broad
"""
        
        elif error_type == "timeout":
            prompt += """
GUIDANCE: The request timed out. Consider:
- Simplifying the request
- Breaking it into smaller parts
- Using a faster alternative tool if available
"""
        
        elif error_type == "tool_execution_error":
            prompt += """
GUIDANCE: The tool returned an error. This usually means:
- Invalid parameter values (check the error message)
- Missing required context
- Tool-specific constraint violation

Analyze the error message carefully and adjust parameters accordingly.
"""
        
        if context:
            prompt += f"\n\nADDITIONAL CONTEXT:\n{json.dumps(context, indent=2)}\n"
        
        prompt += "\nPlease generate a corrected tool call that addresses the error."
        
        return prompt
    
    async def _generate_openai(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate correction using OpenAI"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert at correcting tool calls based on execution errors."},
                {"role": "user", "content": prompt}
            ],
            tools=available_tools,
            tool_choice="auto"
        )
        
        if response.choices[0].message.tool_calls:
            tc = response.choices[0].message.tool_calls[0]
            return {
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments)
            }
        
        return {}
    
    async def _generate_anthropic(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate correction using Anthropic"""
        # Convert to Anthropic format
        anthropic_tools = []
        for tool in available_tools:
            func = tool["function"]
            anthropic_tools.append({
                "name": func["name"],
                "description": func["description"],
                "input_schema": func["parameters"]
            })
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            tools=anthropic_tools
        )
        
        for content_block in response.content:
            if content_block.type == "tool_use":
                return {
                    "name": content_block.name,
                    "arguments": content_block.input
                }
        
        return {}
    
    def get_correction_stats(self) -> Dict[str, Any]:
        """Get statistics about corrections"""
        if not self.correction_history:
            return {"total_corrections": 0}
        
        error_types = {}
        tools_corrected = {}
        
        for correction in self.correction_history:
            # Count error types
            error_type = correction["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
            # Count tools
            tool_name = correction["original"].get("name", "unknown")
            tools_corrected[tool_name] = tools_corrected.get(tool_name, 0) + 1
        
        return {
            "total_corrections": len(self.correction_history),
            "by_error_type": error_types,
            "by_tool": tools_corrected
        }

