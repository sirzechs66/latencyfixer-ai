"""
Health Router

Health check and API info endpoints.
"""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Health check and API info."""
    return {
        "service": "LatencyFixer AI",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "analyze": "POST /analyze",
            "health": "GET /health",
            "benchmark": "GET /test-cases/benchmark",
            "test-cases": "GET /test-cases"
        }
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}