"""
Simple Comparison: Baseline vs Middleware

Shows what happens when baseline fails vs what middleware does.
"""

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.test_dataset import get_test_dataset


class SimpleSimulator:
    """Simple failure simulator"""
    
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.failures = ["timeout", "rate_limit", "api_error", "transient"]
        self.messages = {
            "timeout": "Connection timeout after 30s",
            "rate_limit": "Rate limit exceeded",
            "api_error": "503 Service Unavailable",
            "transient": "Temporary network error"
        }
    
    def execute(self, tool, args, attempt=1):
        """Execute with 35% failure rate, lower on retries"""
        failure_rate = 0.35 if attempt == 1 else 0.10
        
        if self.rng.random() < failure_rate:
            error_type = self.rng.choice(self.failures)
            return {
                "success": False,
                "error": self.messages[error_type],
                "error_type": error_type
            }
        
        return {"success": True, "result": f"{tool} succeeded"}


async def test_baseline(tool, args, simulator):
    """Baseline: single attempt, no retry"""
    result = simulator.execute(tool, args, attempt=1)
    return {"success": result["success"], "error": result.get("error"), "attempts": 1}


async def test_middleware(tool, args, simulator):
    """Middleware: retry up to 3 times"""
    for attempt in range(1, 4):
        result = simulator.execute(tool, args, attempt=attempt)
        if result["success"]:
            return {"success": True, "attempts": attempt}
        await asyncio.sleep(0.01)  # Simulate backoff
    
    return {"success": False, "error": result.get("error"), "attempts": 3}


async def run_comparison(num_tests=20):
    print("\n" + "="*80)
    print("BASELINE vs MIDDLEWARE COMPARISON")
    print("="*80)
    print("Running tests until baseline fails, showing what middleware does...\n")
    
    test_cases = get_test_dataset()
    tests_run = 0
    baseline_failures = 0
    middleware_recovered = 0
    middleware_also_failed = 0
    
    while tests_run < num_tests:
        # Pick random test
        test = random.choice(test_cases)
        seed = random.randint(1, 1000000)
        
        # Run both with same seed for fair comparison
        sim_baseline = SimpleSimulator(seed)
        sim_middleware = SimpleSimulator(seed)
        
        baseline = await test_baseline(test.expected_tool, test.expected_params, sim_baseline)
        
        # Only show when baseline fails
        if not baseline["success"]:
            middleware = await test_middleware(test.expected_tool, test.expected_params, sim_middleware)
            
            tests_run += 1
            baseline_failures += 1
            
            print(f"{'─'*80}")
            print(f"Test #{tests_run}: {test.description}")
            print(f"Tool: {test.expected_tool}")
            print(f"{'─'*80}")
            
            # Show baseline failure
            print(f"\n  ❌ BASELINE FAILED")
            print(f"     Attempts: {baseline['attempts']}")
            print(f"     Error: {baseline['error']}")
            
            # Show middleware result
            if middleware["success"]:
                middleware_recovered += 1
                print(f"\n  ✅ MIDDLEWARE SUCCEEDED")
                print(f"     Attempts: {middleware['attempts']}")
                if middleware['attempts'] > 1:
                    print(f"     → Recovered after {middleware['attempts']} attempts")
            else:
                middleware_also_failed += 1
                print(f"\n  ❌ MIDDLEWARE ALSO FAILED")
                print(f"     Attempts: {middleware['attempts']} (exhausted retries)")
                print(f"     Error: {middleware['error']}")
            
            print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nBaseline failures tested:  {baseline_failures}")
    print(f"Middleware recovered:      {middleware_recovered} ({middleware_recovered/baseline_failures*100:.0f}%)")
    print(f"Middleware also failed:    {middleware_also_failed} ({middleware_also_failed/baseline_failures*100:.0f}%)")
    print(f"\n{'='*80}\n")
    
    if middleware_recovered > 0:
        print(f"✅ Middleware recovered {middleware_recovered}/{baseline_failures} failures!")
        print(f"   Recovery rate: {middleware_recovered/baseline_failures*100:.0f}%\n")


if __name__ == "__main__":
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(f"\nRunning {num} baseline failure scenarios...\n")
    asyncio.run(run_comparison(num))

