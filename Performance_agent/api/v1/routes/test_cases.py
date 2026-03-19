"""
Test Cases Router

Endpoints for preloaded test cases and benchmark results.
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from benchmark.compare import BenchmarkRunner


router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.get("")
async def get_test_cases():
    """
    Get preloaded test cases for frontend demo.

    Returns sample log/code pairs for testing the UI.
    """
    test_cases_path = Path(__file__).parent.parent / "benchmark" / "test_cases.json"

    if not test_cases_path.exists():
        return {"test_cases": [], "error": "Test cases file not found"}

    data = json.loads(test_cases_path.read_text())

    # Return simplified format for frontend
    test_cases = []
    for tc in data.get("test_cases", []):
        test_cases.append({
            "name": tc.get("name"),
            "description": tc.get("description"),
            "logs": "\n".join(tc.get("input_logs", [])),
            "code": "\n\n".join(
                f"# {fp}\n{code}"
                for fp, code in tc.get("code_snippets", {}).items()
            )
        })

    return {"test_cases": test_cases}


@router.get("/benchmark")
async def get_benchmark_results():
    """
    Get pre-computed benchmark results from test cases.

    Returns aggregate scores comparing agent vs baseline Claude.
    """
    try:
        runner = BenchmarkRunner()
        results = runner.run_all_test_cases()

        # Calculate aggregate
        avg_agent = sum(r["agent_score"] for r in results) / len(results)
        avg_claude = sum(r["claude_score"] for r in results) / len(results)
        improvement = ((avg_agent - avg_claude) / avg_claude * 100) if avg_claude > 0 else 0

        return {
            "test_cases": results,
            "aggregate": {
                "avg_agent_score": avg_agent,
                "avg_claude_score": avg_claude,
                "improvement_pct": improvement,
                "test_count": len(results)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark failed: {str(e)}"
        )