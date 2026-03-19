# Analyze router: exposes the `/analyze` endpoint for the UI

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from agent.graph import run_latencyfixer


router = APIRouter(prefix="/analyze", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    # Request body for analysis endpoint
    logs: str
    code: str
    system_description: str = ""


class AnalyzeResponse(BaseModel):
    # Response body for analysis endpoint
    root_causes: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]
    fixes: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    final_score: float
    context_used: List[Dict[str, Any]]
    benchmark_comparison: Optional[Dict[str, Any]] = None


@router.post("", response_model=AnalyzeResponse)
async def analyze_performance(request: AnalyzeRequest):
    """
    Analyze performance latency from logs and code.

    - **logs**: Error messages, stack traces, performance warnings
    - **code**: Source code snippets (optional, improves analysis)
    - **system_description**: Context about the system being analyzed

    Returns structured analysis with root causes, bottlenecks, and fixes.
    """
    try:
        # Parse logs into list format
        input_logs = [line.strip() for line in request.logs.split("\n") if line.strip()]

        # Parse code snippets - support single file or multi-file format
        code_snippets = {}
        if request.code:
            import json
            try:
                parsed = json.loads(request.code)
                if isinstance(parsed, dict):
                    code_snippets = parsed
                else:
                    code_snippets = {"pasted_code.py": request.code}
            except json.JSONDecodeError:
                code_snippets = {"pasted_code.py": request.code}

        # Run the agent pipeline
        result = run_latencyfixer(
            input_logs=input_logs,
            code_snippets=code_snippets,
            system_description=request.system_description
        )

        return AnalyzeResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )