"""
Resilient Tool Executor

Handles the 70% - execution failures (network, API errors, timeouts, rate limits)
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json


class ExecutionError(Exception):
    """Base exception for execution errors"""
    pass


class RateLimitError(ExecutionError):
    """Rate limit exceeded"""
    pass


class NetworkTimeout(ExecutionError):
    """Network timeout"""
    pass


class ToolExecutionError(ExecutionError):
    """Tool-specific execution error"""
    pass


class RetryStrategy(Enum):
    """Retry strategies"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR = "linear"
    IMMEDIATE = "immediate"


@dataclass
class ExecutionResult:
    """Result of tool execution"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 1
    total_duration: float = 0.0
    suggest_correction: bool = False


class ResilientToolExecutor:
    """
    Handles execution failures with retry logic, exponential backoff, and timeouts.
    
    This addresses the 70% of real production failures:
    - Network timeouts
    - API rate limits
    - Service unavailable
    - Transient failures
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        timeout: float = 30.0,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.retry_strategy = retry_strategy
        
        # Track execution stats
        self.execution_stats = {}
    
    async def execute_with_retry(
        self,
        tool_call: Dict[str, Any],
        executor_func: Callable,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute tool with retry logic.
        
        Args:
            tool_call: {"name": "tool_name", "arguments": {...}}
            executor_func: Function to execute (e.g., actual API call)
            context: Additional context
        
        Returns:
            ExecutionResult with success/failure info
        """
        tool_name = tool_call.get("name", "unknown")
        start_time = time.time()
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    executor_func(tool_call),
                    timeout=self.timeout
                )
                
                # Success!
                duration = time.time() - start_time
                self._record_success(tool_name, attempt, duration)
                
                return ExecutionResult(
                    success=True,
                    result=result,
                    attempts=attempt,
                    total_duration=duration
                )
            
            except asyncio.TimeoutError:
                last_error = NetworkTimeout(f"Execution timed out after {self.timeout}s")
                error_type = "timeout"
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
            
            except RateLimitError as e:
                last_error = e
                error_type = "rate_limit"
                
                # Always retry rate limits with backoff
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
            
            except ToolExecutionError as e:
                # Tool-specific error - don't retry, feed back to LLM
                duration = time.time() - start_time
                self._record_failure(tool_name, attempt, "tool_error")
                
                return ExecutionResult(
                    success=False,
                    error=str(e),
                    error_type="tool_execution_error",
                    attempts=attempt,
                    total_duration=duration,
                    suggest_correction=True  # LLM should try to fix this
                )
            
            except Exception as e:
                last_error = e
                error_type = "unknown"
                
                # Generic errors - retry with caution
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
        
        # All retries exhausted
        duration = time.time() - start_time
        self._record_failure(tool_name, self.max_retries, error_type)
        
        return ExecutionResult(
            success=False,
            error=str(last_error),
            error_type=error_type,
            attempts=self.max_retries,
            total_duration=duration,
            suggest_correction=False  # Already tried multiple times
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay before retry based on strategy"""
        if self.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        elif self.retry_strategy == RetryStrategy.LINEAR:
            delay = min(self.base_delay * attempt, self.max_delay)
        else:  # IMMEDIATE
            delay = 0
        
        return delay
    
    def _record_success(self, tool_name: str, attempts: int, duration: float):
        """Record successful execution"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "success": 0,
                "failure": 0,
                "total_attempts": 0,
                "avg_duration": 0.0
            }
        
        stats = self.execution_stats[tool_name]
        stats["success"] += 1
        stats["total_attempts"] += attempts
        
        # Update average duration
        total_executions = stats["success"] + stats["failure"]
        stats["avg_duration"] = (
            (stats["avg_duration"] * (total_executions - 1) + duration) / total_executions
        )
    
    def _record_failure(self, tool_name: str, attempts: int, error_type: str):
        """Record failed execution"""
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {
                "success": 0,
                "failure": 0,
                "total_attempts": 0,
                "avg_duration": 0.0,
                "error_types": {}
            }
        
        stats = self.execution_stats[tool_name]
        stats["failure"] += 1
        stats["total_attempts"] += attempts
        
        # Track error types
        if "error_types" not in stats:
            stats["error_types"] = {}
        stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
    
    def get_reliability_score(self, tool_name: str) -> float:
        """Get reliability score for a tool (0.0 to 1.0)"""
        if tool_name not in self.execution_stats:
            return 1.0  # No data, assume reliable
        
        stats = self.execution_stats[tool_name]
        total = stats["success"] + stats["failure"]
        
        if total == 0:
            return 1.0
        
        return stats["success"] / total
    
    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution statistics"""
        if tool_name:
            return self.execution_stats.get(tool_name, {})
        return self.execution_stats


# Mock executor function for testing
async def mock_tool_executor(tool_call: Dict[str, Any]) -> Any:
    """Mock tool executor that simulates various failure modes"""
    tool_name = tool_call.get("name", "")
    arguments = tool_call.get("arguments", {})
    
    # Simulate different behaviors
    if tool_name == "flaky_api":
        # 50% chance of failure
        import random
        if random.random() < 0.5:
            raise ToolExecutionError("API returned 500 error")
    
    elif tool_name == "slow_api":
        # Slow execution
        await asyncio.sleep(2)
    
    elif tool_name == "rate_limited_api":
        # Simulate rate limit
        raise RateLimitError("Rate limit exceeded, retry after 60s")
    
    # Default: successful execution
    return {
        "tool": tool_name,
        "arguments": arguments,
        "result": f"Successfully executed {tool_name}"
    }

