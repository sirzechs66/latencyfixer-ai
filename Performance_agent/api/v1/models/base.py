"""
Base Pydantic models for LatencyFixer AI.

This module contains:
- Re-exports of core models from agent.models
- LLM-specific request/response models for Bedrock integration
"""

# Re-export from agent.models for backwards compatibility
from agent.models import (
    RootCause,
    Bottleneck,
    OptimizationFix,
    EvaluationMetrics,
    ExtractedEntity,
    DependencyContext,
    BenchmarkResult,
)

# Aliases for model names used in other parts of the codebase
RootCauseModel = RootCause
BottleneckModel = Bottleneck
OptimizationFixModel = OptimizationFix
EvaluationMetricsModel = EvaluationMetrics
EntityModel = ExtractedEntity
DependencyContextModel = DependencyContext
BenchmarkResultModel = BenchmarkResult

# =============================================================================
# LLM REQUEST/RESPONSE MODELS (for Bedrock integration)
# =============================================================================

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class LLMAnalysisRequest(BaseModel):
    """
    Request model for LLM-based analysis.

    Sent to Claude via Bedrock for analysis.
    """
    logs: List[str]
    code_context: Dict[str, str]
    system_prompt: str = "You are a performance analysis expert."


class LLMAnalysisResponse(BaseModel):
    """
    Response model from LLM-based analysis.

    Parsed response from Claude via Bedrock.
    """
    root_causes: List[RootCauseModel]
    bottlenecks: List[BottleneckModel]
    analysis_summary: str = ""


__all__ = [
    "RootCauseModel",
    "BottleneckModel",
    "OptimizationFixModel",
    "EvaluationMetricsModel",
    "EntityModel",
    "DependencyContextModel",
    "BenchmarkResultModel",
    "RootCause",
    "Bottleneck",
    "OptimizationFix",
    "EvaluationMetrics",
    "ExtractedEntity",
    "DependencyContext",
    "BenchmarkResult",
    "LLMAnalysisRequest",
    "LLMAnalysisResponse",
]