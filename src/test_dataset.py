"""
Test Dataset for Evaluating Tool Calling

Defines test cases with ground truth for evaluation.
Each test case includes:
- User query
- Expected tool name
- Expected parameters
- Common errors to test for
"""

from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class TestCase:
    """A single test case for tool calling evaluation"""
    query: str
    expected_tool: str
    expected_params: Dict[str, Any]
    error_types_tested: List[str]  # Which error types this tests for
    description: str


# Test dataset with diverse error patterns
TEST_DATASET = [
    # Test 1: Basic correct usage
    TestCase(
        query="What's the weather like in London?",
        expected_tool="get_weather",
        expected_params={"location": "London"},  # Units optional - not specified by user
        error_types_tested=["missing_required_parameter"],
        description="Basic weather query - should correctly identify location"
    ),
    
    # Test 2: Missing required parameter trap
    TestCase(
        query="Search for information about artificial intelligence",
        expected_tool="search_web",
        expected_params={"query": "artificial intelligence"},  # num_results optional
        error_types_tested=["missing_required_parameter"],
        description="Search query - must have specific query parameter"
    ),
    
    # Test 3: Wrong parameter type
    TestCase(
        query="Calculate the result of 25 times 4",
        expected_tool="calculator",
        expected_params={"expression": "25 * 4"},
        error_types_tested=["wrong_parameter_type", "invalid_expression"],
        description="Calculator - expression should be string, not separate numbers"
    ),
    
    # Test 4: Date format validation
    TestCase(
        query="Book a table at The French Laundry for December 25th, 2024 at 7:30 PM for 4 people",
        expected_tool="book_restaurant",
        expected_params={
            "restaurant_name": "The French Laundry",
            "date": "2024-12-25",
            "time": "19:30",
            "party_size": 4
        },
        error_types_tested=["invalid_parameter_format", "wrong_parameter_type"],
        description="Restaurant booking - must use correct date/time formats"
    ),
    
    # Test 5: Enum constraint validation
    TestCase(
        query="Get the stock price for Apple on NASDAQ",
        expected_tool="get_stock_price",
        expected_params={"ticker": "AAPL", "exchange": "NASDAQ"},
        error_types_tested=["incorrect_enum_value"],
        description="Stock price - exchange must be from allowed enum values"
    ),
    
    # Test 6: Email format validation
    TestCase(
        query="Send an email to john@example.com with subject 'Meeting Tomorrow' and high priority saying 'Don't forget our 2pm meeting'",
        expected_tool="send_email",
        expected_params={
            "to": "john@example.com",
            "subject": "Meeting Tomorrow",
            "body": "Don't forget our 2pm meeting",
            "priority": "high"
        },
        error_types_tested=["invalid_parameter_format", "incorrect_enum_value"],
        description="Email sending - proper email format and priority enum"
    ),
    
    # Test 7: Ambiguous location (local error) - CONTEXT CRITICAL
    TestCase(
        query="What's the weather in Paris?",
        expected_tool="get_weather",
        expected_params={"location": "Paris,FR"},  # Country code is contextually critical
        error_types_tested=["ambiguous_location", "missing_context_dependency"],
        description="Ambiguous location - should disambiguate to Paris, France (most common)"
    ),
    
    # Test 8: Query too broad (local error) - SHOULD REFINE
    TestCase(
        query="Search for things about climate",
        expected_tool="search_web",
        expected_params={"query": "climate change information"},  # Should refine vague query
        error_types_tested=["query_too_broad"],
        description="Vague search - should refine 'things about climate' to be more specific"
    ),
    
    # Test 9: Range validation
    TestCase(
        query="Book a table at Olive Garden tomorrow at 6 PM for 15 people",
        expected_tool="book_restaurant",
        expected_params={
            "restaurant_name": "Olive Garden",
            "date": "2025-11-10",  # Tomorrow from the system date
            "time": "18:00",
            "party_size": 15
        },
        error_types_tested=["out_of_range_value"],
        description="Large party size - within valid range (1-20)"
    ),
    
    # Test 10: Multiple context dependencies - BOTH CRITICAL
    TestCase(
        query="Look up the weather in New York City and tell me if I need an umbrella",
        expected_tool="get_weather",
        expected_params={"location": "New York City,US", "units": "fahrenheit"},  # Both contextually required
        error_types_tested=["missing_context_dependency", "ambiguous_location"],
        description="US location - should infer country code AND fahrenheit (US convention)"
    ),
    
    # Test 11: Potential hallucinated parameters
    TestCase(
        query="Calculate 100 divided by 5",
        expected_tool="calculator",
        expected_params={"expression": "100 / 5"},
        error_types_tested=["hallucinated_parameters"],
        description="Simple calculation - should not add non-existent parameters like 'precision' or 'format'"
    ),
    
    # Test 12: Complex context extraction
    TestCase(
        query="Send an urgent email to sarah.johnson@company.com about the Q4 report being ready for review",
        expected_tool="send_email",
        expected_params={
            "to": "sarah.johnson@company.com",
            "subject": "Q4 Report Ready for Review",
            "body": "The Q4 report is ready for your review.",
            "priority": "high"
        },
        error_types_tested=["missing_context_dependency", "incorrect_enum_value"],
        description="Email with context - must extract subject, map 'urgent' to 'high' priority"
    ),
    
    # Test 13: Stock ticker format - NO EXCHANGE SPECIFIED
    TestCase(
        query="What's Google's stock price?",
        expected_tool="get_stock_price",
        expected_params={"ticker": "GOOGL"},  # Exchange optional - not specified
        error_types_tested=["missing_context_dependency"],
        description="Stock query - must map 'Google' to ticker 'GOOGL'"
    ),
    
    # Test 14: Temperature units context - CANADIAN CITY
    TestCase(
        query="How cold is it in Toronto?",
        expected_tool="get_weather",
        expected_params={"location": "Toronto,CA", "units": "celsius"},  # Both contextually critical
        error_types_tested=["missing_context_dependency"],
        description="Canadian city - should infer country code AND celsius (Canadian convention)"
    ),
    
    # Test 15: Search with specific number - USER SPECIFIED COUNT
    TestCase(
        query="Find me the top 3 results for machine learning courses",
        expected_tool="search_web",
        expected_params={"query": "machine learning courses", "num_results": 3},  # User said "top 3"
        error_types_tested=["missing_context_dependency", "wrong_parameter_type"],
        description="User specified 'top 3' - must extract num_results=3 as integer"
    ),
]


def get_test_dataset() -> List[TestCase]:
    """Get the complete test dataset"""
    return TEST_DATASET


def get_tests_by_error_type(error_type: str) -> List[TestCase]:
    """Get test cases that check for a specific error type"""
    return [tc for tc in TEST_DATASET if error_type in tc.error_types_tested]

