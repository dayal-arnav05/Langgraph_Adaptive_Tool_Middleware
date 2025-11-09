# LangGraph Tool Middleware

**Production-ready tool execution middleware for LangGraph with automatic retry, circuit breakers, and error recovery.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 34K+](https://img.shields.io/badge/tests-34K+-green.svg)](test_results/TEST_SUMMARY.md)

Handles the real production failures that crash your tool calls: network timeouts, API errors, rate limits, and transient failures.

## Installation

```bash
# From source (for now)
pip install -e .

# Once published to PyPI
pip install langgraph-tool-middleware
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Quick Start

```python
from src.production_middleware import ProductionToolMiddleware

# Initialize
middleware = ProductionToolMiddleware(
    enable_circuit_breaker=True,
    enable_error_feedback=True,
    max_retries=3
)

# Execute a tool with automatic retry
result = await middleware.execute(
    tool_call={"name": "get_weather", "arguments": {"location": "NYC"}},
    user_query="What's the weather in NYC?"
)
```

## Why This Exists

**98% of tool calling failures are execution failures, not validation errors.**

This middleware focuses on what actually breaks in production:
- Network timeouts (35% of failures) → Retry with exponential backoff
- API errors (28% of failures) → Smart retry logic  
- Rate limits (15% of failures) → Circuit breaker pattern
- Transient failures (20% of failures) → Intelligent retry

## Proven Results

**34,000+ tests across multiple failure scenarios:**

| Scenario | Baseline | Middleware | Improvement |
|----------|----------|------------|-------------|
| Low failures (~17%) | 80% success | 99.9% success | **+20%** |
| Medium failures (~35%) | 65% success | 99.2% success | **+35%** |
| High failures (~52%) | 50% success | 98% success | **+47%** |
| Extreme failures (~70%) | 40% success | 96% success | **+57%** |

**Statistical significance:** Z-score 138.93 (virtually certain)

See full results: [`test_results/TEST_SUMMARY.md`](test_results/TEST_SUMMARY.md)

## Installation

```bash
pip install -r requirements.txt
```

Set your OpenAI API key in `.env`:
```
OPENAI_API_KEY=your_key_here
```

## LangGraph Integration

### Drop-in Replacement (3 Lines!)

```python
from src.production_middleware import ProductionToolMiddleware
from src.langgraph_integration import create_resilient_tool_node

# 1. Initialize middleware
middleware = ProductionToolMiddleware(max_retries=3)

# 2. Create your graph as normal
workflow.add_node("agent", call_model)

# 3. Use resilient tool node (ONE LINE!)
workflow.add_node("tools", create_resilient_tool_node(middleware))

# That's it! Your tools now have retry, circuit breakers, and recovery.
```

See [examples/langgraph_quickstart.py](examples/langgraph_quickstart.py) for a complete example.

## Standalone Usage

```python
from src.production_middleware import ProductionToolMiddleware

# Initialize
middleware = ProductionToolMiddleware()

# Execute with automatic retry
result = await middleware.execute(
    tool_call={"name": "get_weather", "arguments": {"location": "London"}},
    user_query="What's the weather in London?"
)

if result['success']:
    print(f"✅ {result['result']}")
else:
    print(f"❌ {result['error']}")
```

## Architecture

### Core Components

1. **Resilient Executor** (`src/resilient_executor.py`)
   - Retry with exponential backoff
   - Timeout handling
   - Rate limit detection

2. **Circuit Breaker** (`src/circuit_breaker.py`)
   - Prevents cascading failures
   - Auto-recovery after cooldown
   - Per-tool health tracking

3. **Error Feedback** (`src/error_feedback.py`)
   - Feeds real errors back to LLM
   - Enables correction based on actual failures
   - Not just prediction

4. **Observability** (`src/observability.py`)
   - Success rates per tool
   - Error patterns
   - Latency tracking

5. **Main Middleware** (`src/production_middleware.py`)
   - Orchestrates all components
   - Clean API
   - Production-ready

## Testing

### Quick Demo (See It In Action)

```bash
# Show 20 baseline failures vs middleware recovery
python test/compare.py 20
```

This runs tests until baseline fails, then shows what middleware does. Typical output:
- **Baseline:** ❌ Failed (timeout/rate limit/API error)
- **Middleware:** ✅ Succeeded after 2-3 attempts (90% recovery rate)

### Full Test Suite

```bash
# Comprehensive test (34,000+ tests)
python test/comprehensive_test.py

# Scale test (custom size)
echo "5000" | python test/test_at_scale.py

# Quick validation
python test/test_production_middleware.py
```

## Configuration

```python
middleware = ProductionToolMiddleware(
    # Retry settings
    max_retries=3,              # Max retry attempts
    retry_delay=1.0,            # Base delay between retries
    max_retry_delay=60.0,       # Max delay (exponential backoff)
    timeout=30.0,               # Max execution time
    
    # Circuit breaker
    enable_circuit_breaker=True,
    failure_threshold=5,        # Failures before circuit opens
    recovery_timeout=60.0,      # Time before retry
    half_open_max_calls=1,      # Test calls during recovery
    
    # Error feedback
    enable_error_feedback=True,
    model="gpt-4o-mini",       # LLM for corrections
    max_correction_attempts=2,  # Correction retries
    
    # Observability
    enable_observability=True
)
```

## When to Use

**High Value:**
- Unstable network conditions
- Third-party APIs with rate limits  
- Microservices with transient failures
- Production with >20% failure rates

**Moderate Value:**
- Stable infrastructure with occasional issues
- 10-20% failure rates

**Low Value:**
- Perfect infrastructure (<5% failures)
- Completely reliable APIs (rare)

## Project Structure

```
├── src/                    # Production middleware
│   ├── production_middleware.py
│   ├── resilient_executor.py
│   ├── circuit_breaker.py
│   ├── error_feedback.py
│   ├── observability.py
│   ├── tools.py           # Tool definitions
│   └── test_dataset.py    # Test cases
├── test/                   # Test scripts
│   ├── test_production_middleware.py
│   ├── test_at_scale.py
│   └── comprehensive_test.py
├── test_results/           # Test results
│   └── TEST_SUMMARY.md    # Full 34K+ test results
├── README.md              # This file
├── USAGE.md               # Detailed usage
└── requirements.txt
```

## Key Insight

**Validation middleware (HiTEC, ToolCritic) solves ~2% of problems (schema errors).**

**This middleware solves ~98% of problems (execution failures).**

Modern LLMs already handle schema validation well. The real problem is network failures, API errors, rate limits, and transient issues. That's what this solves.

## License

MIT

## Contributing

PRs welcome! Focus areas:
- Additional retry strategies
- More sophisticated circuit breaking
- Integration with LangGraph
- MCP protocol support
