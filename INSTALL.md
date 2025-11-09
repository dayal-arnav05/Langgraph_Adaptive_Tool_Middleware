# Installation Guide

## Quick Install

### From PyPI (once published)

```bash
pip install langgraph-tool-middleware
```

### From Source (for development)

```bash
# Clone the repository
git clone https://github.com/yourusername/langgraph-tool-middleware.git
cd langgraph-tool-middleware

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Requirements

- Python 3.8+
- OpenAI API key (for error feedback feature)

## Setup

1. **Create `.env` file:**

```bash
OPENAI_API_KEY=your_api_key_here
```

2. **Verify installation:**

```bash
python -c "from src.production_middleware import ProductionToolMiddleware; print('✅ Installed successfully')"
```

## Usage

### Basic Usage (Standalone)

```python
from src.production_middleware import ProductionToolMiddleware

# Initialize
middleware = ProductionToolMiddleware()

# Execute a tool
result = await middleware.execute(
    tool_call={"name": "get_weather", "arguments": {"location": "NYC"}},
    user_query="What's the weather in NYC?"
)
```

### LangGraph Integration

```python
from langgraph.graph import StateGraph
from src.production_middleware import ProductionToolMiddleware

# Initialize middleware
middleware = ProductionToolMiddleware(
    enable_circuit_breaker=True,
    enable_error_feedback=True,
    max_retries=3
)

# Create tool execution node
async def execute_tools(state):
    tool_calls = state["messages"][-1].tool_calls
    
    tool_messages = []
    for tool_call in tool_calls:
        result = await middleware.execute(
            tool_call=tool_call,
            user_query=state["messages"][0].content
        )
        # Convert to LangGraph message format
        tool_messages.append(ToolMessage(
            content=result["result"] if result["success"] else result["error"],
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": tool_messages}

# Add to your graph
workflow.add_node("tools", execute_tools)
```

## Examples

Run the included examples:

```bash
# Simple standalone usage
python examples/simple_usage.py

# LangGraph integration
python examples/langgraph_integration.py
```

## Configuration

Full configuration options:

```python
middleware = ProductionToolMiddleware(
    # Retry settings
    max_retries=3,              # Max retry attempts
    retry_delay=1.0,            # Base delay between retries (seconds)
    max_retry_delay=60.0,       # Max delay for exponential backoff
    timeout=30.0,               # Max execution time per attempt
    
    # Circuit breaker
    enable_circuit_breaker=True,
    failure_threshold=5,        # Failures before circuit opens
    recovery_timeout=60.0,      # Cooldown before retry
    half_open_max_calls=1,      # Test calls during recovery
    
    # Error feedback (requires API key)
    enable_error_feedback=True,
    model="gpt-4o-mini",       # LLM for error correction
    max_correction_attempts=2,
    
    # Observability
    enable_observability=True
)
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're in the right directory:

```bash
cd /path/to/langgraph-tool-middleware
python -c "import sys; print(sys.path)"
```

### API Key Issues

If error feedback doesn't work:

```bash
# Check if API key is set
python -c "import os; print('API key:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

### Test Installation

Run the test suite:

```bash
# Quick validation
python test/test_production_middleware.py

# Visual comparison
python test/compare.py 10

# Full scale test
echo "1000" | python test/test_at_scale.py
```

## Next Steps

- See [README.md](README.md) for overview
- See [USAGE.md](USAGE.md) for detailed documentation
- Check [examples/](examples/) for more examples
- Review [test_results/TEST_SUMMARY.md](test_results/TEST_SUMMARY.md) for proof of value

## Publishing to PyPI

For maintainers:

```bash
# Build package
python -m build

# Upload to PyPI
python -m twine upload dist/*

# Or test on TestPyPI first
python -m twine upload --repository testpypi dist/*
```

