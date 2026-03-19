# Analyzer engine — I added pattern libs for common issues and a small LLM fallback.
# This file implements lightweight bottleneck detection and root-cause heuristics.

import re
from typing import List, Dict, Any, Optional
import logging

from agent.models import RootCause, Bottleneck
from parsers.extractors import LogPatterns, CodeAnalyzer

# Optional Bedrock integration
try:
    from integrations.bedrock_client import BedrockClient
    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False


# Builtin pattern libraries (simple, human-curated)

class BottleneckPatternLibrary:
    # Known bottleneck regexes and metadata

    PATTERNS = {
        "io_wait": {
            "patterns": [
                r"waiting\s+for\s+(?:socket|stream)",
                r"blocked\s+on\s+I/O",
                r"timeout",
            ],
            "category": "io",
            "impact": "latency",
        },
        "n_plus_one": {
            "patterns": [
                r"loop.*(?:query|fetch)",
                r"foreach.*(?:api|db)",
            ],
            "category": "algorithm",
            "impact": "latency",
        },
        "inefficient_algorithm": {
            "patterns": [
                r"O\([nN]\^2\)",
                r"nested\s+loops",
                r"quadratic",
            ],
            "category": "algorithm",
            "impact": "throughput",
        },
        "concurrency": {
            "patterns": [
                r"lock\s+contention",
                r"race\s+condition",
                r"deadlock",
            ],
            "category": "concurrency",
            "impact": "latency",
        },
        "streaming": {
            "patterns": [
                r"stream.*buffer",
                r"chunk.*size",
                r"buffer.*overflow",
            ],
            "category": "io",
            "impact": "latency",
        },
    }


class RootCausePatternLibrary:
    # Root-cause indicator patterns and common causes

    PATTERNS = {
        "io": {
            "indicators": [
                r"socket\s+timeout",
                r"connection\s+(?:refused|reset)",
                r"DNS\s+resolution",
                r"file\s+descriptor",
            ],
            "common_causes": [
                "Blocking I/O in async path",
                "Missing connection pooling",
                "Unbuffered I/O operations",
            ]
        },
        "compute": {
            "indicators": [
                r"CPU\s+bound",
                r"high\s+cpu\s+usage",
                r"computation\s+heavy",
            ],
            "common_causes": [
                "Expensive calculations in hot path",
                "Missing caching/memoization",
                "Inefficient algorithm",
            ]
        },
        "memory": {
            "indicators": [
                r"memory\s+leak",
                r"GC\s+pressure",
                r"out\s+of\s+memory",
            ],
            "common_causes": [
                "Unbounded cache growth",
                "Circular references",
                "Large object allocations in loops",
            ]
        },
        "concurrency": {
            "indicators": [
                r"thread\s+contention",
                r"lock\s+waiting",
                r"async\s+timeout",
            ],
            "common_causes": [
                "Lock contention",
                "Race conditions",
                "Missing async/await",
            ]
        },
        "algorithm": {
            "indicators": [
                r"O\(n\^2\)",
                r"exponential",
                r"inefficient\s+loop",
            ],
            "common_causes": [
                "Nested loops",
                "Suboptimal data structures",
                "Redundant computations",
            ]
        },
    }


# Analyzer engine (main orchestration)

class AnalyzerEngine:
    # Main analysis engine — combines pattern matching and code heuristics

    logger = logging.getLogger(__name__)

    def __init__(self):
        self.bottleneck_library = BottleneckPatternLibrary()
        self.root_cause_library = RootCausePatternLibrary()
        self.code_analyzer = CodeAnalyzer()
        self.patterns = LogPatterns()

    def analyze_logs(
        self,
        logs: List[str],
        dependency_context: Dict[str, Any]
    ) -> tuple[List[RootCause], List[Bottleneck]]:
        """Analyze logs and context to find bottlenecks and root causes."""
        root_causes = []
        bottlenecks = []

        # Combine context for analysis
        self.logger.debug("Analyzing logs: %d lines; context files: %d", len(logs), len(dependency_context))
        full_context = "\n".join([
            getattr(ctx, "content", "") for ctx in dependency_context.values()
        ]) + "\n".join(logs)

        # Pattern-based detection
        for bottleneck_type, config in self.bottleneck_library.PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, full_context, re.IGNORECASE):
                    # Extract timing if available
                    timing_match = re.search(
                        self.patterns.TIMING_MS,
                        full_context,
                        re.IGNORECASE
                    )
                    impact_ms = (
                        float(timing_match.group(1))
                        if timing_match
                        else 50.0
                    )

                    # Determine severity
                    severity = self._classify_severity(impact_ms)

                    bottlenecks.append(Bottleneck(
                        description=f"Detected {bottleneck_type.replace('_', '')} pattern",
                        location=full_context[:100],
                        severity=severity,
                        impact_type=config["impact"],
                        estimated_impact_ms=impact_ms
                    ))

                    root_causes.append(RootCause(
                        description=f"{bottleneck_type.replace('_', '')} causing latency",
                        category=config["category"],
                        confidence=0.75,
                        evidence=[f"Pattern match: {pattern}"],
                        file_path=None,
                        function_name=None
                    ))

        # Code anti-pattern detection
        for file_path, ctx in dependency_context.items():
            content = getattr(ctx, "content", "")
            code_issues = self.code_analyzer.detect_anti_patterns(content)

            for issue in code_issues:
                if issue["pattern"] == "nested_loops":
                    root_causes.append(RootCause(
                        description="Nested loop detected - potential O(n²) complexity",
                        category="algorithm",
                        confidence=0.6,
                        evidence=["Multiple sequential for loops"],
                        file_path=file_path,
                        function_name=None
                    ))

                if issue["pattern"] == "blocking_calls":
                    for call in self.code_analyzer.detect_blocking_calls(content):
                        bottlenecks.append(Bottleneck(
                            description=f"Blocking call: {call}",
                            location=f"{file_path}:unknown",
                            severity="medium",
                            impact_type="latency",
                            estimated_impact_ms=50.0
                        ))

        return root_causes, bottlenecks

    def _classify_severity(self, impact_ms: float) -> str:
        """Classify severity based on impact in milliseconds."""
        thresholds = {
            "critical": 500,
            "high": 200,
            "medium": 50,
            "low": 10,
        }

        if impact_ms > thresholds["critical"]:
            return "critical"
        elif impact_ms > thresholds["high"]:
            return "high"
        elif impact_ms > thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def analyze_code_file(
        self,
        file_path: str,
        content: str
    ) -> List[RootCause]:
        """Analyze a single code file for potential issues."""
        root_causes = []

        anti_patterns = self.code_analyzer.detect_anti_patterns(content)

        for issue in anti_patterns:
            root_causes.append(RootCause(
                description=issue["description"],
                category="algorithm" if "loop" in issue["pattern"] else "io",
                confidence=0.6,
                evidence=[issue["pattern"]],
                file_path=file_path,
                function_name=None
            ))

        return root_causes

    def analyze_with_llm(
        self,
        logs: List[str],
        code_context: Dict[str, str],
        use_bedrock: bool = False,
    ) -> tuple[List[RootCause], List[Bottleneck]]:
        """
        Analyze using LLM (Claude via Bedrock or fallback pattern-based).

        Args:
            logs: List of log strings
            code_context: Dictionary of file_path -> code content
            use_bedrock: If True, use AWS Bedrock for analysis

        Returns:
            Tuple of (root_causes, bottlenecks)
        """
        if use_bedrock and BEDROCK_AVAILABLE:
            try:
                self.logger.info("Attempting Bedrock LLM analysis (use_bedrock=%s)", use_bedrock)
                client = BedrockClient()
                response = client.analyze_performance(
                    logs=logs,
                    code_context=code_context,
                )
                self.logger.info("Bedrock analysis succeeded: %d root_causes, %d bottlenecks", len(response.root_causes), len(response.bottlenecks))
                return response.root_causes, response.bottlenecks
            except Exception as e:
                # Fallback to pattern-based analysis
                self.logger.warning("Bedrock analysis failed: %s; falling back to pattern-based", e)

        # Fallback to pattern-based analysis
        self.logger.info("Using pattern-based analysis fallback")
        return self.analyze_logs(logs, code_context)
