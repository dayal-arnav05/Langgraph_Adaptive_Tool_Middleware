"""
Circuit Breaker Pattern for Tool Execution

Prevents cascading failures by temporarily disabling broken tools.
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Tool is broken, reject calls
    HALF_OPEN = "half_open"  # Testing if tool recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing from half-open
    timeout: float = 60.0  # Seconds before trying again
    half_open_max_calls: int = 3  # Max calls in half-open state


class ToolCircuitBreaker:
    """
    Circuit breaker for tool execution.
    
    Prevents calling tools that are repeatedly failing:
    - CLOSED: Normal operation
    - OPEN: Tool broken, reject all calls
    - HALF_OPEN: Testing recovery, allow limited calls
    
    This prevents cascading failures and wasted API calls.
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        
        # Track state per tool
        self.states: Dict[str, CircuitState] = defaultdict(lambda: CircuitState.CLOSED)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.last_failure_time: Dict[str, float] = {}
        self.half_open_calls: Dict[str, int] = defaultdict(int)
        
        # Statistics
        self.total_rejected = 0
        self.rejections_per_tool: Dict[str, int] = defaultdict(int)
    
    def can_execute(self, tool_name: str) -> tuple[bool, Optional[str]]:
        """
        Check if tool can be executed.
        
        Returns:
            (can_execute, reason_if_not)
        """
        state = self.states[tool_name]
        
        if state == CircuitState.CLOSED:
            return True, None
        
        elif state == CircuitState.OPEN:
            # Check if timeout has passed
            if tool_name in self.last_failure_time:
                time_since_failure = time.time() - self.last_failure_time[tool_name]
                
                if time_since_failure >= self.config.timeout:
                    # Transition to HALF_OPEN
                    self.states[tool_name] = CircuitState.HALF_OPEN
                    self.half_open_calls[tool_name] = 0
                    return True, None
            
            # Still broken
            self.total_rejected += 1
            self.rejections_per_tool[tool_name] += 1
            
            return False, f"Circuit breaker OPEN for {tool_name} (too many failures)"
        
        elif state == CircuitState.HALF_OPEN:
            # Allow limited calls to test recovery
            if self.half_open_calls[tool_name] < self.config.half_open_max_calls:
                self.half_open_calls[tool_name] += 1
                return True, None
            
            # Max calls reached in half-open
            self.total_rejected += 1
            self.rejections_per_tool[tool_name] += 1
            
            return False, f"Circuit breaker HALF_OPEN for {tool_name} (max test calls reached)"
    
    def record_success(self, tool_name: str):
        """Record successful execution"""
        state = self.states[tool_name]
        
        if state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_counts[tool_name] = 0
        
        elif state == CircuitState.HALF_OPEN:
            # Increment success count
            self.success_counts[tool_name] += 1
            
            # Check if we can close the circuit
            if self.success_counts[tool_name] >= self.config.success_threshold:
                self.states[tool_name] = CircuitState.CLOSED
                self.failure_counts[tool_name] = 0
                self.success_counts[tool_name] = 0
                self.half_open_calls[tool_name] = 0
    
    def record_failure(self, tool_name: str, error_type: Optional[str] = None):
        """Record failed execution"""
        state = self.states[tool_name]
        
        self.failure_counts[tool_name] += 1
        self.last_failure_time[tool_name] = time.time()
        
        if state == CircuitState.CLOSED:
            # Check if we should open the circuit
            if self.failure_counts[tool_name] >= self.config.failure_threshold:
                self.states[tool_name] = CircuitState.OPEN
                return {"action": "circuit_opened", "tool": tool_name}
        
        elif state == CircuitState.HALF_OPEN:
            # Failure during recovery test - reopen circuit
            self.states[tool_name] = CircuitState.OPEN
            self.success_counts[tool_name] = 0
            self.half_open_calls[tool_name] = 0
            return {"action": "circuit_reopened", "tool": tool_name}
        
        return None
    
    def reset(self, tool_name: str):
        """Manually reset circuit breaker for a tool"""
        self.states[tool_name] = CircuitState.CLOSED
        self.failure_counts[tool_name] = 0
        self.success_counts[tool_name] = 0
        self.half_open_calls[tool_name] = 0
        if tool_name in self.last_failure_time:
            del self.last_failure_time[tool_name]
    
    def get_state(self, tool_name: str) -> Dict[str, any]:
        """Get current state for a tool"""
        return {
            "state": self.states[tool_name].value,
            "failure_count": self.failure_counts[tool_name],
            "success_count": self.success_counts[tool_name],
            "last_failure": self.last_failure_time.get(tool_name),
            "rejections": self.rejections_per_tool.get(tool_name, 0)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        return {
            "total_rejected": self.total_rejected,
            "tools_monitored": len(self.states),
            "open_circuits": sum(1 for s in self.states.values() if s == CircuitState.OPEN),
            "half_open_circuits": sum(1 for s in self.states.values() if s == CircuitState.HALF_OPEN),
            "per_tool_rejections": dict(self.rejections_per_tool)
        }

