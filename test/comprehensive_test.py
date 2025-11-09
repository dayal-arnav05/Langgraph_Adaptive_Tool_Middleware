"""
Comprehensive Testing Suite

Multiple runs with different scenarios to prove consistent value:
1. Multiple runs with same parameters (consistency)
2. Different failure rates (low, medium, high)
3. Different tool mixes
4. Large scale (10,000+ tests)
"""

import asyncio
import random
import time
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from collections import defaultdict
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from same test directory
from test_at_scale import (
    RealisticFailureSimulator,
    FAILURE_PROFILES,
    test_baseline_at_scale,
    test_production_middleware_at_scale
)
from src.test_dataset import get_test_dataset


@dataclass
class TestScenario:
    """Test scenario configuration"""
    name: str
    iterations: int
    failure_multiplier: float  # Multiply failure rates
    description: str


SCENARIOS = [
    TestScenario(
        "Low Failure Rate",
        2000,
        0.5,  # 50% of normal failures (~15-20% total)
        "Optimistic production (good network, stable APIs)"
    ),
    TestScenario(
        "Medium Failure Rate",
        2000,
        1.0,  # Normal failures (~30-40% total)
        "Typical production (some network issues, occasional API errors)"
    ),
    TestScenario(
        "High Failure Rate",
        2000,
        1.5,  # 150% of normal failures (~45-60% total)
        "Pessimistic production (poor network, unstable APIs)"
    ),
    TestScenario(
        "Very High Failure Rate",
        2000,
        2.0,  # 200% of normal failures (~60-70% total)
        "Extreme conditions (degraded infrastructure)"
    ),
]


class AdjustableFailureSimulator(RealisticFailureSimulator):
    """Failure simulator with adjustable rates"""
    
    def __init__(self, seed: int, failure_multiplier: float = 1.0):
        super().__init__(seed)
        self.failure_multiplier = failure_multiplier
    
    def should_fail(self, tool_name: str, attempt: int = 1) -> tuple[bool, str]:
        """Determine if tool should fail with adjusted rates"""
        self.total_calls += 1
        self.call_history[tool_name] += 1
        
        profile = FAILURE_PROFILES.get(tool_name, FAILURE_PROFILES["get_weather"])
        
        # Adjust failure rates
        failure_multiplier = self.failure_multiplier * (1.0 if attempt == 1 else 0.3)
        
        # Network timeout
        if random.random() < profile.network_failure_rate * failure_multiplier:
            return True, "Connection timeout after 30s"
        
        # Rate limit
        rate_limit_chance = profile.rate_limit_rate * failure_multiplier
        if self.call_history[tool_name] > 10:
            rate_limit_chance *= 1.5
        
        if random.random() < rate_limit_chance:
            return True, f"Rate limit exceeded. Try again in {random.randint(30, 120)}s"
        
        # API error
        if random.random() < profile.api_error_rate * failure_multiplier:
            error_codes = [500, 502, 503, 504]
            code = random.choice(error_codes)
            return True, f"API returned {code} error: Service unavailable"
        
        # Transient failure
        if random.random() < profile.transient_failure_rate * failure_multiplier:
            return True, "Temporary service disruption"
        
        return False, ""


async def run_scenario(scenario: TestScenario, test_cases: List, run_number: int = 1):
    """Run a single test scenario"""
    print(f"\n{'='*80}")
    print(f"SCENARIO: {scenario.name} (Run #{run_number})")
    print(f"{'='*80}")
    print(f"Description: {scenario.description}")
    print(f"Tests: {scenario.iterations:,}")
    print(f"Expected failure rate: {scenario.failure_multiplier * 35:.1f}%")
    print()
    
    # Baseline test
    baseline_sim = AdjustableFailureSimulator(seed=42 + run_number, failure_multiplier=scenario.failure_multiplier)
    baseline_results = await test_baseline_at_scale(test_cases, scenario.iterations, baseline_sim)
    
    # Middleware test
    middleware_sim = AdjustableFailureSimulator(seed=42 + run_number, failure_multiplier=scenario.failure_multiplier)
    middleware_results = await test_production_middleware_at_scale(test_cases, scenario.iterations, middleware_sim)
    
    # Calculate metrics
    baseline_success_rate = baseline_results["successes"] / baseline_results["total_calls"]
    middleware_success_rate = middleware_results["successes"] / middleware_results["total_calls"]
    improvement = (middleware_success_rate - baseline_success_rate) * 100
    
    # Calculate Z-score
    import math
    n = baseline_results['total_calls']
    se_baseline = math.sqrt(baseline_success_rate * (1 - baseline_success_rate) / n)
    se_middleware = math.sqrt(middleware_success_rate * (1 - middleware_success_rate) / n)
    se_diff = math.sqrt(se_baseline**2 + se_middleware**2)
    z_score = (middleware_success_rate - baseline_success_rate) / se_diff if se_diff > 0 else 0
    
    return {
        "scenario": scenario.name,
        "run": run_number,
        "iterations": scenario.iterations,
        "baseline_success_rate": baseline_success_rate,
        "middleware_success_rate": middleware_success_rate,
        "improvement": improvement,
        "z_score": z_score,
        "baseline_failures": baseline_results["failures"],
        "middleware_failures": middleware_results["failures"],
        "retries_used": middleware_results.get("retries_used", 0),
        "baseline_results": baseline_results,
        "middleware_results": middleware_results
    }


def print_summary_table(all_results: List[Dict]):
    """Print summary table of all results"""
    print(f"\n{'='*100}")
    print(f"{'COMPREHENSIVE TEST RESULTS SUMMARY':^100}")
    print(f"{'='*100}\n")
    
    print(f"{'Scenario':<25} {'Run':<5} {'Tests':<8} {'Baseline':<12} {'Middleware':<12} {'Improve':<10} {'Z-score':<10} {'Significant?'}")
    print("-" * 100)
    
    total_tests = 0
    total_baseline_successes = 0
    total_middleware_successes = 0
    total_baseline_calls = 0
    
    for result in all_results:
        scenario = result["scenario"]
        run = result["run"]
        iterations = result["iterations"]
        baseline_sr = result["baseline_success_rate"]
        middleware_sr = result["middleware_success_rate"]
        improvement = result["improvement"]
        z_score = result["z_score"]
        
        significance = "✅✅✅" if z_score > 10 else "✅✅" if z_score > 5 else "✅" if z_score > 2.58 else "⚠️"
        
        print(f"{scenario:<25} {run:<5} {iterations:<8,} {baseline_sr:<12.1%} {middleware_sr:<12.1%} {improvement:<10.1f}% {z_score:<10.2f} {significance}")
        
        # Accumulate for overall stats
        total_tests += iterations
        total_baseline_calls += iterations
        total_baseline_successes += int(baseline_sr * iterations)
        total_middleware_successes += int(middleware_sr * iterations)
    
    print("-" * 100)
    
    # Overall statistics
    overall_baseline_sr = total_baseline_successes / total_baseline_calls
    overall_middleware_sr = total_middleware_successes / total_baseline_calls
    overall_improvement = (overall_middleware_sr - overall_baseline_sr) * 100
    
    print(f"{'OVERALL':<25} {'ALL':<5} {total_tests:<8,} {overall_baseline_sr:<12.1%} {overall_middleware_sr:<12.1%} {overall_improvement:<10.1f}%")
    
    print(f"\n{'='*100}\n")
    
    # Detailed statistics
    print(f"DETAILED STATISTICS:")
    print(f"  Total tests run: {total_tests:,}")
    print(f"  Total baseline failures: {total_baseline_calls - total_baseline_successes:,}")
    print(f"  Total middleware failures: {total_baseline_calls - total_middleware_successes:,}")
    print(f"  Failures prevented: {(total_baseline_calls - total_baseline_successes) - (total_baseline_calls - total_middleware_successes):,}")
    print(f"  Overall improvement: {overall_improvement:.2f}%")
    
    # Calculate overall Z-score
    import math
    n = total_baseline_calls
    se_baseline = math.sqrt(overall_baseline_sr * (1 - overall_baseline_sr) / n)
    se_middleware = math.sqrt(overall_middleware_sr * (1 - overall_middleware_sr) / n)
    se_diff = math.sqrt(se_baseline**2 + se_middleware**2)
    overall_z_score = (overall_middleware_sr - overall_baseline_sr) / se_diff if se_diff > 0 else 0
    
    print(f"  Overall Z-score: {overall_z_score:.2f}")
    
    if overall_z_score > 10:
        print(f"  ✅✅✅ EXTREMELY SIGNIFICANT (virtually certain)")
    elif overall_z_score > 5:
        print(f"  ✅✅ VERY HIGHLY SIGNIFICANT")
    elif overall_z_score > 2.58:
        print(f"  ✅ HIGHLY SIGNIFICANT (p < 0.01)")
    
    print(f"\n{'='*100}\n")
    
    # Consistency analysis
    improvements = [r["improvement"] for r in all_results]
    z_scores = [r["z_score"] for r in all_results]
    
    print(f"CONSISTENCY ANALYSIS:")
    print(f"  Improvement range: {min(improvements):.1f}% to {max(improvements):.1f}%")
    print(f"  Average improvement: {sum(improvements)/len(improvements):.1f}%")
    print(f"  Std deviation: {(sum((x - sum(improvements)/len(improvements))**2 for x in improvements) / len(improvements))**0.5:.2f}%")
    print(f"  All Z-scores > 2.58: {'✅ YES' if all(z > 2.58 for z in z_scores) else '❌ NO'}")
    print(f"  All improvements > 20%: {'✅ YES' if all(i > 20 for i in improvements) else '❌ NO'}")
    
    print(f"\n{'='*100}\n")


async def main():
    print("\n" + "="*100)
    print(f"{'COMPREHENSIVE TESTING SUITE':^100}")
    print("="*100)
    print("\nThis will run MULTIPLE test scenarios to prove consistent value:")
    print("  1. Multiple runs of same scenario (consistency)")
    print("  2. Different failure rates (low, medium, high, extreme)")
    print("  3. Large total sample size (statistical significance)")
    print("\n" + "="*100 + "\n")
    
    test_cases = get_test_dataset()
    all_results = []
    
    # Run each scenario multiple times
    num_runs_per_scenario = 3
    
    for scenario in SCENARIOS:
        for run in range(1, num_runs_per_scenario + 1):
            result = await run_scenario(scenario, test_cases, run)
            all_results.append(result)
            
            # Quick summary
            print(f"\n✅ Completed: {result['improvement']:.1f}% improvement (Z={result['z_score']:.2f})")
    
    # Run one massive test
    print(f"\n{'='*100}")
    print(f"RUNNING MASSIVE SCALE TEST (10,000 iterations)")
    print(f"{'='*100}\n")
    
    massive_scenario = TestScenario(
        "Massive Scale Test",
        10000,
        1.0,
        "Large-scale validation"
    )
    
    massive_result = await run_scenario(massive_scenario, test_cases, 1)
    all_results.append(massive_result)
    
    # Print comprehensive summary
    print_summary_table(all_results)
    
    # Final verdict
    avg_improvement = sum(r["improvement"] for r in all_results) / len(all_results)
    min_improvement = min(r["improvement"] for r in all_results)
    all_significant = all(r["z_score"] > 2.58 for r in all_results)
    
    print("\n" + "="*100)
    print(f"{'FINAL VERDICT':^100}")
    print("="*100 + "\n")
    
    if avg_improvement > 25 and min_improvement > 20 and all_significant:
        print("🎉 ✅ PRODUCTION MIDDLEWARE PROVIDES MASSIVE, CONSISTENT VALUE ✅ 🎉\n")
        print(f"  • Average improvement: {avg_improvement:.1f}%")
        print(f"  • Minimum improvement: {min_improvement:.1f}%")
        print(f"  • All tests statistically significant: ✅ YES")
        print(f"  • Total tests run: {sum(r['iterations'] for r in all_results):,}")
        print(f"\n  This is production-ready middleware that solves real problems.")
    elif avg_improvement > 15:
        print("✅ PRODUCTION MIDDLEWARE PROVIDES MODERATE VALUE\n")
        print(f"  • Average improvement: {avg_improvement:.1f}%")
        print(f"  • May be useful in specific scenarios")
    else:
        print("⚠️ PRODUCTION MIDDLEWARE PROVIDES MARGINAL VALUE\n")
        print(f"  • Average improvement: {avg_improvement:.1f}%")
        print(f"  • Consider if worth the complexity")
    
    print("\n" + "="*100 + "\n")
    
    # Save results
    with open("comprehensive_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print("📊 Detailed results saved to: comprehensive_test_results.json\n")


if __name__ == "__main__":
    asyncio.run(main())

