"""
Analyzer Node for LatencyFixer AI.

Detects performance bottlenecks and identifies root causes from
the retrieved context and input logs.
"""

import json
import re
from typing import List, Dict, Optional, Any
from pathlib import Path

from .state import AgentState, RootCause, Bottleneck


class AnalyzerNode:
    """
    Analyzer node that processes context to detect bottlenecks
    and identify root causes of latency issues.
    """

    # Bottleneck pattern library
    BOTTLENECK_PATTERNS = {
        "io_wait": {
            "patterns": [
                r"waiting\s+for\s+(?:socket|stream|connection)",
                r"blocked\s+on\s+I/O",
                r"read\s+timeout",
                r"write\s+timeout",
                r"connection\s+(?:refused|timed\s*out)",
            ],
            "category": "io",
            "impact": "latency",
        },
        "n_plus_one": {
            "patterns": [
                r"loop.*(?:query|fetch|request)",
                r"foreach.*(?:api|db|query)",
                r"iteration.*(?:select|fetch)",
            ],
            "category": "algorithm",
            "impact": "latency",
        },
        "inefficient_algorithm": {
            "patterns": [
                r"O\([nN]\^2\)",
                r"quadratic",
                r"nested\s+loops",
                r"repeated\s+computation",
                r"redundant\s+processing",
            ],
            "category": "algorithm",
            "impact": "throughput",
        },
        "memory_pressure": {
            "patterns": [
                r"memory\s+allocation",
                r"heap\s+size",
                r"garbage\s+collection",
                r"OOM|out\s+of\s+memory",
                r"memory\s+leak",
            ],
            "category": "memory",
            "impact": "latency",
        },
        "concurrency": {
            "patterns": [
                r"lock\s+contention",
                r"deadlock",
                r"race\s+condition",
                r"thread\s+blocked",
                r"async.*await",
                r"event\s+loop.*blocked",
            ],
            "category": "concurrency",
            "impact": "latency",
        },
        "serialization": {
            "patterns": [
                r"json\.loads|json\.dumps",
                r"pickle",
                r"serialization",
                r"deserialization",
                r"marshal",
            ],
            "category": "compute",
            "impact": "latency",
        },
        "network": {
            "patterns": [
                r"HTTP\s+(?:GET|POST)",
                r"request.*latency",
                r"round\s+trip",
                r"DNS\s+lookup",
                r"SSL\s+handshake",
            ],
            "category": "io",
            "impact": "latency",
        },
        "streaming": {
            "patterns": [
                r"stream.*buffer",
                r"chunk.*size",
                r"yield.*delay",
                r"async.*stream",
                r"generator.*latency",
            ],
            "category": "io",
            "impact": "latency",
        },
        "audio_video": {
            "patterns": [
                r"audio.*overlap",
                r"video.*stutter",
                r"buffer.*underrun",
                r"frame.*drop",
                r"sync.*issue",
            ],
            "category": "concurrency",
            "impact": "latency",
        },
    }

    SEVERITY_THRESHOLDS = {
        "critical": 500,  # ms
        "high": 200,
        "medium": 50,
        "low": 10,
    }

    def __init__(self, prompt_template_path: Optional[str] = None):
        """
        Initialize the analyzer node.

        Args:
            prompt_template_path: Optional path to custom prompt template
        """
        self.template_path = prompt_template_path
        self._load_template()

    def _load_template(self) -> None:
        """Load the analyzer prompt template."""
        default_path = Path(__file__).parent.parent / "prompts" / "analyzer.txt"

        if self.template_path and Path(self.template_path).exists():
            self.template = Path(self.template_path).read_text()
        elif default_path.exists():
            self.template = default_path.read_text()
        else:
            self.template = self._get_default_template()

    def _get_default_template(self) -> str:
        """Return default analyzer prompt template."""
        return """
Analyze the following context and logs to identify root causes and bottlenecks.

CONTEXT:
{context}

LOGS:
{logs}

CODE SNIPPETS:
{code}

Identify:
1. Root causes of latency issues
2. Performance bottlenecks
3. Categorize each finding (io, compute, memory, concurrency, algorithm)
4. Assign confidence scores based on evidence

Output as JSON with root_causes[] and bottlenecks[] arrays.
"""

    def analyze(self, state: AgentState) -> AgentState:
        """
        Analyze the context and logs to detect bottlenecks and root causes.

        Args:
            state: Agent state with populated context

        Returns:
            Updated state with root causes and bottlenecks
        """
        # Combine all context for analysis
        full_context = self._build_analysis_context(state)

        # Pattern-based analysis
        self._pattern_analysis(state, full_context)

        # Code-based analysis
        self._code_analysis(state)

        # Log-based analysis
        self._log_analysis(state)

        # Cross-reference and deduplicate
        self._deduplicate_findings(state)

        return state

    def _build_analysis_context(self, state: AgentState) -> str:
        """Build combined context string for analysis."""
        context_parts = []

        # Add dependency context
        for file_path, ctx in state.dependency_context.items():
            context_parts.append(f"=== {file_path} ===\n{ctx.content[:5000]}")

        # Add logs
        context_parts.append("=== INPUT LOGS ===")
        for log in state.input_logs:
            context_parts.append(log)

        # Add system description
        if state.system_description:
            context_parts.append("=== SYSTEM DESCRIPTION ===")
            context_parts.append(state.system_description)

        return "\n\n".join(context_parts)

    def _pattern_analysis(self, state: AgentState, context: str) -> None:
        """
        Analyze context using pattern matching.

        Detects known bottleneck patterns in logs and code.
        """
        context_lower = context.lower()

        for bottleneck_type, config in self.BOTTLENECK_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, context_lower):
                    # Create bottleneck entry
                    bottleneck = Bottleneck(
                        description=f"Detected {bottleneck_type.replace('_', ' ')} pattern",
                        location=context[:200],  # First 200 chars as location context
                        severity=self._estimate_severity(context, config["impact"]),
                        impact_type=config["impact"],
                        estimated_impact_ms=self._estimate_impact_ms(pattern, context)
                    )
                    state.add_bottleneck(bottleneck)

                    # Create corresponding root cause
                    root_cause = RootCause(
                        description=f"{bottleneck_type.replace('_', '')} is causing latency",
                        category=config["category"],
                        confidence=self._calculate_confidence(pattern, context),
                        evidence=[f"Pattern match: {pattern}"],
                        file_path=self._extract_file_from_context(context)
                    )
                    state.add_root_cause(root_cause)

    def _code_analysis(self, state: AgentState) -> None:
        """
        Analyze code snippets for performance anti-patterns.

        Looks for:
        - Nested loops
        - Unnecessary allocations
        - Blocking calls in async code
        - Missing caching
        """
        for file_path, ctx in state.dependency_context.items():
            content = ctx.content

            # Check for nested loops (O(n²) pattern)
            nested_loop_pattern = r'for\s+\w+\s+in\s+.+?:\s+for\s+\w+\s+in\s+.+?:'
            if re.search(nested_loop_pattern, content, re.DOTALL):
                state.add_bottleneck(Bottleneck(
                    description="Nested loop detected - potential O(n²) complexity",
                    location=file_path,
                    severity="high",
                    impact_type="throughput",
                    estimated_impact_ms=100
                ))
                state.add_root_cause(RootCause(
                    description="Quadratic algorithm complexity",
                    category="algorithm",
                    confidence=0.85,
                    evidence=["Nested loop pattern in code"],
                    file_path=file_path
                ))

            # Check for blocking calls
            blocking_patterns = [
                (r'time\.sleep', "Blocking sleep call"),
                (r'requests\.(get|post|put|delete)', "Synchronous HTTP request"),
                (r'open\s*\(.+?\).*read', "Synchronous file read"),
                (r'socket\.connect', "Blocking socket connection"),
            ]

            for pattern, description in blocking_patterns:
                if re.search(pattern, content):
                    state.add_bottleneck(Bottleneck(
                        description=description,
                        location=file_path,
                        severity="medium",
                        impact_type="latency",
                        estimated_impact_ms=50
                    ))

            # Check for missing caching
            if re.search(r'def\s+\w+.*:.*\n\s+.*(?:return|yield)', content):
                if "cache" not in content.lower() and "memo" not in content.lower():
                    # Heuristic: pure function without caching
                    if re.search(r'return\s+\w+\s*\*', content):  # Expensive computation hint
                        state.add_root_cause(RootCause(
                            description="Expensive computation without caching",
                            category="compute",
                            confidence=0.6,
                            evidence=["No caching detected for expensive operation"],
                            file_path=file_path
                        ))

    def _log_analysis(self, state: AgentState) -> None:
        """
        Analyze input logs for latency indicators.

        Extracts timing information and error patterns.
        """
        timing_pattern = r'(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?)'

        for log in state.input_logs:
            # Extract timing information
            timings = re.findall(timing_pattern, log, re.IGNORECASE)
            if timings:
                max_timing = max(float(t) for t in timings)

                # Determine severity based on timing
                if max_timing > self.SEVERITY_THRESHOLDS["critical"]:
                    severity = "critical"
                elif max_timing > self.SEVERITY_THRESHOLDS["high"]:
                    severity = "high"
                elif max_timing > self.SEVERITY_THRESHOLDS["medium"]:
                    severity = "medium"
                else:
                    severity = "low"

                state.add_bottleneck(Bottleneck(
                    description=f"Latency of {max_timing:.1f}ms detected in logs",
                    location=log[:100],
                    severity=severity,
                    impact_type="latency",
                    estimated_impact_ms=max_timing
                ))

            # Check for error patterns
            error_patterns = [
                (r'timeout', "Timeout error"),
                (r'connection\s+(?:refused|reset)', "Connection failure"),
                (r'memory\s+error', "Memory error"),
                (r'deadlock', "Deadlock detected"),
            ]

            for pattern, error_type in error_patterns:
                if re.search(pattern, log, re.IGNORECASE):
                    state.add_root_cause(RootCause(
                        description=error_type,
                        category="io" if "connection" in pattern or "timeout" in pattern else "memory",
                        confidence=0.9,
                        evidence=[f"Log contains: {pattern}"],
                        file_path=None
                    ))

    def _estimate_severity(self, context: str, impact_type: str) -> str:
        """Estimate severity based on context."""
        # Check for severity indicators in context
        severity_indicators = {
            "critical": ["crash", "fatal", "critical", "emergency"],
            "high": ["severe", "major", "significant", "high"],
            "medium": ["moderate", "medium", "noticeable"],
            "low": ["minor", "low", "slight", "negligible"],
        }

        context_lower = context.lower()
        for severity, indicators in severity_indicators.items():
            for indicator in indicators:
                if indicator in context_lower:
                    return severity

        return "medium"  # Default

    def _estimate_impact_ms(self, pattern: str, context: str) -> float:
        """Estimate latency impact in milliseconds."""
        # Try to extract actual timing from context
        timing_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?)', context, re.IGNORECASE)
        if timing_match:
            return float(timing_match.group(1))

        # Default estimates based on pattern type
        if "timeout" in pattern:
            return 5000  # Timeout typically 5s
        if "n_plus_one" in pattern or "loop" in pattern:
            return 200  # N+1 queries typically 200ms+
        if "nested" in pattern or "O(" in pattern:
            return 100  # Algorithm issues 100ms+
        if "stream" in pattern or "buffer" in pattern:
            return 50  # Streaming latency 50ms
        if "audio" in pattern or "overlap" in pattern:
            return 20  # Audio issues typically 20ms

        return 50  # Default

    def _calculate_confidence(self, pattern: str, context: str) -> float:
        """Calculate confidence score for a finding."""
        confidence = 0.5  # Base confidence

        # Increase confidence for multiple matches
        matches = len(re.findall(pattern, context, re.IGNORECASE))
        confidence += min(matches * 0.1, 0.3)

        # Increase confidence for stack trace evidence
        if "stack" in context.lower() or "traceback" in context.lower():
            confidence += 0.1

        # Cap at 0.95
        return min(confidence, 0.95)

    def _extract_file_from_context(self, context: str) -> Optional[str]:
        """Extract file path from context."""
        match = re.search(r'File\s+"([^"]+)"', context)
        if match:
            return match.group(1)

        match = re.search(r'in\s+\w+\s+at\s+([^:\s]+)', context)
        if match:
            return match.group(1)

        return None

    def _deduplicate_findings(self, state: AgentState) -> None:
        """Remove duplicate root causes and bottlenecks."""
        # Deduplicate root causes
        unique_causes = []
        seen_descriptions = set()

        for cause in state.root_causes:
            key = f"{cause.description}:{cause.category}"
            if key not in seen_descriptions:
                unique_causes.append(cause)
                seen_descriptions.add(key)

        state.root_causes = unique_causes

        # Deduplicate bottlenecks
        unique_bottlenecks = []
        seen_locations = set()

        for bottleneck in state.bottlenecks:
            key = f"{bottleneck.location}:{bottleneck.description}"
            if key not in seen_locations:
                unique_bottlenecks.append(bottleneck)
                seen_locations.add(key)

        state.bottlenecks = unique_bottlenecks

    def get_analysis_summary(self, state: AgentState) -> str:
        """
        Get human-readable analysis summary.

        Args:
            state: Agent state with analysis results

        Returns:
            Formatted summary string
        """
        lines = ["=== Analysis Results ===\n"]

        lines.append(f"Root Causes Found: {len(state.root_causes)}")
        for i, cause in enumerate(state.root_causes, 1):
            lines.append(f"\n{i}. {cause.description}")
            lines.append(f"   Category: {cause.category}")
            lines.append(f"   Confidence: {cause.confidence:.0%}")
            if cause.file_path:
                lines.append(f"   Location: {cause.file_path}")

        lines.append(f"\n\nBottlenecks Detected: {len(state.bottlenecks)}")
        for i, bottleneck in enumerate(state.bottlenecks, 1):
            lines.append(f"\n{i}. {bottleneck.description}")
            lines.append(f"   Severity: {bottleneck.severity}")
            lines.append(f"   Impact: {bottleneck.impact_type}")
            lines.append(f"   Estimated: {bottleneck.estimated_impact_ms:.1f}ms")

        return "\n".join(lines)
