"""
Tool Execution Observability

Track what's actually happening in production.
"""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict


@dataclass
class ToolExecutionSpan:
    """Represents a single tool execution trace"""
    span_id: str
    tool_name: str
    arguments: Dict[str, Any]
    user_query: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 1
    result_size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolObservability:
    """
    Comprehensive observability for tool execution.
    
    Tracks:
    - Execution traces (spans)
    - Success/failure rates
    - Latency percentiles
    - Error patterns
    - Tool reliability over time
    """
    
    def __init__(self):
        self.spans: List[ToolExecutionSpan] = []
        self.active_spans: Dict[str, ToolExecutionSpan] = {}
        
        # Aggregated metrics
        self.tool_metrics = defaultdict(lambda: {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0.0,
            "durations": [],
            "errors": defaultdict(int)
        })
    
    def start_span(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_query: str
    ) -> str:
        """Start tracking a tool execution"""
        span_id = str(uuid.uuid4())
        
        span = ToolExecutionSpan(
            span_id=span_id,
            tool_name=tool_name,
            arguments=arguments,
            user_query=user_query,
            start_time=time.time()
        )
        
        self.active_spans[span_id] = span
        self.log_event("tool_execution_start", span.to_dict())
        
        return span_id
    
    def end_span(
        self,
        span_id: str,
        success: bool,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        attempts: int = 1
    ):
        """End tracking a tool execution"""
        if span_id not in self.active_spans:
            return
        
        span = self.active_spans[span_id]
        span.end_time = time.time()
        span.duration = span.end_time - span.start_time
        span.success = success
        span.error = error
        span.error_type = error_type
        span.attempts = attempts
        
        if result is not None:
            span.result_size = len(str(result))
        
        # Move to completed spans
        self.spans.append(span)
        del self.active_spans[span_id]
        
        # Update metrics
        self._update_metrics(span)
        
        # Log completion
        event_type = "tool_execution_success" if success else "tool_execution_failure"
        self.log_event(event_type, span.to_dict())
    
    def _update_metrics(self, span: ToolExecutionSpan):
        """Update aggregated metrics"""
        metrics = self.tool_metrics[span.tool_name]
        
        metrics["calls"] += 1
        if span.success:
            metrics["successes"] += 1
        else:
            metrics["failures"] += 1
            if span.error_type:
                metrics["errors"][span.error_type] += 1
        
        if span.duration:
            metrics["total_duration"] += span.duration
            metrics["durations"].append(span.duration)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event (can be extended to send to external systems)"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "data": data
        }
        
        # For now, just print (in production, send to logging service)
        # print(json.dumps(log_entry))
        pass
    
    def get_tool_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific tool or all tools"""
        if tool_name:
            return self._format_metrics(tool_name, self.tool_metrics[tool_name])
        
        return {
            tool: self._format_metrics(tool, metrics)
            for tool, metrics in self.tool_metrics.items()
        }
    
    def _format_metrics(self, tool_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format metrics for display"""
        calls = metrics["calls"]
        if calls == 0:
            return {"calls": 0}
        
        durations = metrics["durations"]
        
        return {
            "tool": tool_name,
            "calls": calls,
            "success_rate": metrics["successes"] / calls,
            "failure_rate": metrics["failures"] / calls,
            "avg_duration": metrics["total_duration"] / calls if calls > 0 else 0,
            "p50_duration": self._percentile(durations, 0.5) if durations else 0,
            "p95_duration": self._percentile(durations, 0.95) if durations else 0,
            "p99_duration": self._percentile(durations, 0.99) if durations else 0,
            "error_breakdown": dict(metrics["errors"])
        }
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall summary"""
        total_calls = sum(m["calls"] for m in self.tool_metrics.values())
        total_successes = sum(m["successes"] for m in self.tool_metrics.values())
        total_failures = sum(m["failures"] for m in self.tool_metrics.values())
        
        return {
            "total_calls": total_calls,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": total_successes / total_calls if total_calls > 0 else 0,
            "tools_used": len(self.tool_metrics),
            "active_spans": len(self.active_spans),
            "completed_spans": len(self.spans)
        }
    
    def get_recent_failures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent failures for debugging"""
        failures = [span for span in self.spans if not span.success]
        recent = sorted(failures, key=lambda s: s.start_time, reverse=True)[:limit]
        return [span.to_dict() for span in recent]

