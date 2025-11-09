# HiTEC Usage Guide

## Quick Start

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or ANTHROPIC_API_KEY
```

### 2. Run Demo

See HiTEC in action with a simple demo:

```bash
python demo.py
```

This will show side-by-side comparisons of baseline vs HiTEC-ICL on sample queries.

### 3. Run Full Experiment

Run the complete evaluation on the test dataset:

```bash
# Run both baseline and HiTEC
python run_experiment.py

# Run only HiTEC
python run_experiment.py --mode hitec

# Run only baseline
python run_experiment.py --mode baseline

# Use different model
python run_experiment.py --model gpt-4o

# Use Anthropic/Claude
python run_experiment.py --provider anthropic --model claude-3-5-sonnet-20241022

# Run on subset of tests (for quick testing)
python run_experiment.py --num-tests 5
```

### 4. View Results

Results are saved to the `results/` directory:

- `baseline_results.json` - Baseline performance
- `hitec_results.json` - HiTEC-ICL performance  
- `comparison.json` - Side-by-side comparison

## Using HiTEC in Your Code

### Baseline Tool Calling

```python
from src.baseline_caller import BaselineToolCaller

caller = BaselineToolCaller(model="gpt-4o-mini")
result = caller.call_tool("What's the weather in London?")

tool_call = result["final_tool_call"]
print(f"Tool: {tool_call['name']}")
print(f"Arguments: {tool_call['arguments']}")
```

### HiTEC-ICL Tool Calling

```python
from src.error_checklists import create_default_checklists
from src.hitec_icl import HiTEC_ICL

# Create error checklists
global_checklist, local_checklist = create_default_checklists()

# Initialize HiTEC
hitec = HiTEC_ICL(
    global_checklist=global_checklist,
    local_checklist=local_checklist,
    model="gpt-4o-mini"
)

# Call with error checking (2 rounds)
result = hitec.call_with_error_checking("What's the weather in London?")

# Get final refined tool call
tool_call = result["final_tool_call"]
print(f"Tool: {tool_call['name']}")
print(f"Arguments: {tool_call['arguments']}")

# See what changed in Round 2
round1_call = result["round_1"]["tool_calls"][0]
if round1_call != tool_call:
    print("Tool call was refined!")
```

### Adding Custom Tools

```python
from src.tools import ToolDefinition, ToolParameter

# Define your tool
my_tool = ToolDefinition(
    name="my_custom_tool",
    description="Does something useful",
    parameters=[
        ToolParameter(
            name="param1",
            type="string",
            description="First parameter",
            required=True
        ),
        ToolParameter(
            name="param2",
            type="integer",
            description="Second parameter",
            required=False
        )
    ]
)

# Add to SAMPLE_TOOLS list or pass custom tools to caller
custom_tools = [my_tool.to_function_schema()]
result = hitec.call_with_error_checking(
    "Your query here",
    available_tools=custom_tools
)
```

### Adding Custom Error Checks

```python
from src.error_checklists import ErrorCheck

# Add global error check
global_checklist.checks.append(
    ErrorCheck(
        error_type="my_custom_error",
        description="Description of the error pattern",
        examples=["Example 1", "Example 2"]
    )
)

# Add tool-specific error check
local_checklist.add_tool_error(
    "my_tool_name",
    ErrorCheck(
        error_type="tool_specific_error",
        description="Common mistake with this tool",
        examples=["Example of the mistake"]
    )
)
```

## Expected Results

Based on the paper's findings, you should see:

- **Parameter Accuracy**: Up to 42% improvement
- **Tool Name Accuracy**: Consistent high accuracy
- **Execution Success Rate**: Significant improvement due to better parameter filling

The improvements are most notable for:
- Date/time format issues
- Ambiguous inputs
- Missing required parameters
- Enum constraint violations

## Next Steps: LangGraph Integration

After validating the results, this can be mounted as middleware for LangGraph:

1. Wrap HiTEC as a LangGraph node
2. Insert before tool execution nodes
3. Use error checklists to catch issues before tool calls
4. Accumulate errors in local checklist from real executions

See the main README for the roadmap.

