"""
AWS Bedrock client for Claude integration.

This module provides:
- Bedrock runtime client for invoking Claude models
- Structured request/response handling
- Error handling and retry logic
"""

import os
import json
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from models.base import LLMAnalysisRequest, LLMAnalysisResponse, RootCauseModel, BottleneckModel


# =============================================================================
# BEDROCK CONFIGURATION
# =============================================================================

class BedrockConfig:
    """Bedrock configuration settings."""

    DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    DEFAULT_REGION = "us-east-1"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.1

    SUPPORTED_MODELS = {
        "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    }


# =============================================================================
# BEDROCK CLIENT
# =============================================================================

class BedrockClient:
    """Client for AWS Bedrock runtime API."""

    def __init__(
        self,
        region_name: Optional[str] = None,
        model_id: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        Initialize Bedrock client.

        Args:
            region_name: AWS region name (defaults to AWS_DEFAULT_REGION env var)
            model_id: Bedrock model ID (defaults to AWS_BEDROCK_MODEL env var)
            access_key: AWS access key (defaults to AWS_ACCESS_KEY_ID env var)
            secret_key: AWS secret key (defaults to AWS_SECRET_ACCESS_KEY env var)
        """
        # Load from environment if not provided
        import os
        self.region_name = region_name or os.environ.get("AWS_DEFAULT_REGION", BedrockConfig.DEFAULT_REGION)
        self.model_id = model_id or os.environ.get("AWS_BEDROCK_MODEL", BedrockConfig.DEFAULT_MODEL_ID)

        # Initialize Bedrock runtime client with credentials
        if access_key or secret_key:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region_name,
                aws_access_key_id=access_key or os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY"),
            )
        else:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=self.region_name,
            )

    def invoke_claude(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = BedrockConfig.DEFAULT_MAX_TOKENS,
        temperature: float = BedrockConfig.DEFAULT_TEMPERATURE,
    ) -> str:
        """
        Invoke Claude model via Bedrock.

        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        # Build request body for Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        if system_prompt:
            request_body["system"] = system_prompt

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read().decode("utf-8"))
            return response_body["content"][0]["text"]

        except ClientError as e:
            if e.error_code == "ThrottlingException":
                raise RuntimeError("Bedrock API rate limit exceeded") from e
            elif e.error_code == "ValidationException":
                raise RuntimeError(f"Invalid request: {e.message}") from e
            else:
                raise RuntimeError(f"Bedrock API error: {str(e)}") from e

    def analyze_performance(
        self,
        logs: List[str],
        code_context: Dict[str, str],
        system_prompt: str = "You are a performance analysis expert specializing in identifying latency bottlenecks and root causes in Python applications.",
    ) -> LLMAnalysisResponse:
        """
        Analyze performance issues using Claude via Bedrock.

        Args:
            logs: List of log strings
            code_context: Dictionary of file_path -> code content
            system_prompt: System prompt for the analysis

        Returns:
            Parsed LLMAnalysisResponse with root causes and bottlenecks
        """
        # Build the prompt
        prompt = self._build_analysis_prompt(logs, code_context)

        messages = [{
            "role": "user",
            "content": prompt
        }]

        # Invoke Claude
        response_text = self.invoke_claude(
            messages=messages,
            system_prompt=system_prompt,
        )

        # Parse the response
        return self._parse_analysis_response(response_text)

    def _build_analysis_prompt(
        self,
        logs: List[str],
        code_context: Dict[str, str],
    ) -> str:
        """Build the analysis prompt for Claude."""
        prompt_parts = []

        # Add logs
        prompt_parts.append("=== LOGS AND ERROR MESSAGES ===")
        for log in logs:
            prompt_parts.append(log)

        # Add code context
        prompt_parts.append("\n=== CODE CONTEXT ===")
        for file_path, content in code_context.items():
            prompt_parts.append(f"\n--- File: {file_path} ---")
            prompt_parts.append(content)

        # Add instructions
        prompt_parts.append("\n=== ANALYSIS INSTRUCTIONS ===")
        prompt_parts.append("""
Analyze the logs and code to identify:

1. ROOT CAUSES - For each root cause, provide:
   - description: Clear description of the root cause
   - category: One of "io", "compute", "memory", "concurrency", "algorithm"
   - confidence: 0.0-1.0 confidence score
   - evidence: List of evidence from logs/code
   - file_path: Affected file (if applicable)
   - function_name: Affected function (if applicable)

2. BOTTLENECKS - For each bottleneck, provide:
   - description: Clear description of the bottleneck
   - location: File:function:line or description
   - severity: "critical", "high", "medium", or "low"
   - impact_type: "latency", "throughput", "memory", or "cpu"
   - estimated_impact_ms: Estimated impact in milliseconds

Respond in JSON format with this structure:
{
    "root_causes": [...],
    "bottlenecks": [...],
    "analysis_summary": "Brief summary of findings"
}
""")

        return "\n".join(prompt_parts)

    def _parse_analysis_response(self, response_text: str) -> LLMAnalysisResponse:
        """Parse Claude's response into structured format."""
        try:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)

            # Parse root causes
            root_causes = [
                RootCauseModel(
                    description=rc.get("description", ""),
                    category=rc.get("category", "unknown"),
                    confidence=float(rc.get("confidence", 0.5)),
                    evidence=rc.get("evidence", []),
                    file_path=rc.get("file_path"),
                    function_name=rc.get("function_name"),
                )
                for rc in parsed.get("root_causes", [])
            ]

            # Parse bottlenecks
            bottlenecks = [
                BottleneckModel(
                    description=bn.get("description", ""),
                    location=bn.get("location", ""),
                    severity=bn.get("severity", "medium"),
                    impact_type=bn.get("impact_type", "latency"),
                    estimated_impact_ms=float(bn.get("estimated_impact_ms", 0)),
                )
                for bn in parsed.get("bottlenecks", [])
            ]

            return LLMAnalysisResponse(
                root_causes=root_causes,
                bottlenecks=bottlenecks,
                analysis_summary=parsed.get("analysis_summary", ""),
            )

        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: return empty analysis with error in summary
            return LLMAnalysisResponse(
                root_causes=[],
                bottlenecks=[],
                analysis_summary=f"Failed to parse response: {str(e)}",
            )


# =============================================================================
# ASYNC BEDROCK CLIENT (for async workflows)
# =============================================================================

class AsyncBedrockClient:
    """Async client for AWS Bedrock runtime API."""

    def __init__(
        self,
        region_name: str = BedrockConfig.DEFAULT_REGION,
        model_id: str = BedrockConfig.DEFAULT_MODEL_ID,
    ):
        self.region_name = region_name
        self.model_id = model_id

        # Initialize async session
        import aioboto3
        self.session = aioboto3.Session()

    async def invoke_claude(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "",
        max_tokens: int = BedrockConfig.DEFAULT_MAX_TOKENS,
        temperature: float = BedrockConfig.DEFAULT_TEMPERATURE,
    ) -> str:
        """
        Async invoke Claude model via Bedrock.
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        if system_prompt:
            request_body["system"] = system_prompt

        async with self.session.client("bedrock-runtime", region_name=self.region_name) as client:
            response = await client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response["body"].read().decode("utf-8"))
            return response_body["content"][0]["text"]
