"""
Integrations for LatencyFixer AI.

This package contains integrations with external services:
- AWS Bedrock for Claude API access
"""

from .bedrock_client import BedrockClient, AsyncBedrockClient, BedrockConfig

__all__ = [
    "BedrockClient",
    "AsyncBedrockClient",
    "BedrockConfig",
]
