"""
Parser and retriever utilities for the LatencyFixer AI agent.

This module contains:
- Log parsing utilities
- Entity extraction from stack traces
- Dependency graph building
- Code analysis utilities
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

from agent.models import ExtractedEntity, DependencyContext  # Pydantic models


# =============================================================================
# REGEX PATTERNS
# =============================================================================

class LogPatterns:
    """Regex patterns for log parsing."""

    # File path patterns
    FILE_PATH = r"[/\\]?(?:[\w.-]+[/\\])+[\w.-]+\.py"

    # Function call patterns
    FUNCTION_CALL = r"(\w+)\s*\("

    # Stack trace pattern: File "path", line N, in function
    STACK_TRACE = r"File\s+\"([^\"]+)\",\s+line\s+(\d+),\s+in\s+(\w+)"

    # Timing patterns: 1234ms or 1.5s
    TIMING_MS = r"(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?)"
    TIMING_S = r"(\d+(?:\.\d+)?)\s*(?:s|seconds?)"

    # Error patterns
    ERROR_PATTERN = r"(?:ERROR|ERR|FATAL|Exception|Traceback)"

    # Performance warning patterns
    PERF_PATTERN = r"(?:PERF|PERFORMANCE|SLOW|timeout|took\s+\d+)"

    # Bottleneck indicators
    BOTTLENECK_PATTERNS = {
        "io_wait": r"waiting\s+for\s+(?:socket|stream)|blocked\s+on\s+I/O|timeout",
        "n_plus_one": r"loop.*(?:query|fetch)|foreach.*(?:api|db)",
        "inefficient_algorithm": r"O\([nN]\^2\)|nested\s+loops|quadratic",
        "concurrency": r"lock\s+contention|race\s+condition|deadlock",
        "streaming": r"stream.*buffer|chunk.*size|buffer.*overflow",
    }


# =============================================================================
# ENTITY EXTRACTOR
# =============================================================================

class EntityExtractor:
    """Extracts entities from logs and stack traces."""

    def __init__(self):
        self.patterns = LogPatterns()
        self.entities: List[ExtractedEntity] = []

    def extract_from_logs(self, logs: List[str]) -> List[ExtractedEntity]:
        """Extract all entities from a list of log lines."""
        self.entities = []

        for log_idx, log in enumerate(logs):
            self._extract_from_single_log(log, log_idx)

        return self.entities

    def _extract_from_single_log(self, log: str, log_idx: int) -> None:
        """Extract entities from a single log line."""
        # Extract stack traces
        for match in re.findall(self.patterns.STACK_TRACE, log):
            file_path, line_num, func_name = match

            self.entities.append(ExtractedEntity(
                entity_type="file",
                name=file_path,
                source=f"log_{log_idx}",
                line_number=int(line_num),
                confidence=0.95
            ))

            self.entities.append(ExtractedEntity(
                entity_type="function",
                name=func_name,
                source=f"log_{log_idx}",
                line_number=int(line_num),
                confidence=0.9
            ))

        # Extract file paths
        for file_path in re.findall(self.patterns.FILE_PATH, log):
            if not any(e["name"] == file_path and e["entity_type"] == "file"
                      for e in self.entities):
                self.entities.append(ExtractedEntity(
                    entity_type="file",
                    name=file_path,
                    source=f"log_{log_idx}",
                    confidence=0.85
                ))

        # Extract function calls
        for func_name in re.findall(self.patterns.FUNCTION_CALL, log):
            self.entities.append(ExtractedEntity(
                entity_type="function",
                name=func_name,
                source=f"log_{log_idx}",
                confidence=0.7
            ))

    def get_unique_entities(self) -> List[ExtractedEntity]:
        """Return unique entities (deduplicated by name and type)."""
        seen: Set[Tuple[str, str]] = set()
        unique = []

        for entity in self.entities:
            key = (entity.name, entity.entity_type)
            if key not in seen:
                seen.add(key)
                unique.append(entity)

        return unique


# =============================================================================
# DEPENDENCY GRAPH BUILDER
# =============================================================================

class DependencyGraphBuilder:
    """Builds shallow dependency graphs from code."""

    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth
        self.import_pattern = re.compile(r"^(?:import|from)\s+(\S+)")

    def extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Python code."""
        imports = []
        for line in content.split("\n"):
            match = self.import_pattern.match(line.strip())
            if match:
                imports.append(match.group(1))
        return imports

    def extract_functions(self, content: str) -> List[Dict[str, str]]:
        """Extract function definitions from Python code."""
        functions = []
        func_pattern = re.compile(r"^def\s+(\w+)\s*\(")

        for line_num, line in enumerate(content.split("\n"), 1):
            match = func_pattern.match(line.strip())
            if match:
                functions.append({
                    "name": match.group(1),
                    "line": str(line_num)
                })

        return functions

    def build_context(
        self,
        file_path: str,
        content: str,
        code_snippets: Dict[str, str]
    ) -> DependencyContext:
        """Build dependency context for a file."""
        imports = self.extract_imports(content)
        functions = self.extract_functions(content)

        # Simple token estimation (4 chars ≈ 1 token for code)
        token_count = len(content) // 4

        return DependencyContext(
            primary_file=file_path,
            content=content[:5000],  # Truncate for context
            imports=imports,
            related_functions=functions,
            token_count=token_count,
            depth=0
        )

    def build_all_contexts(
        self,
        code_snippets: Dict[str, str]
    ) -> Dict[str, DependencyContext]:
        """Build dependency contexts for all code snippets."""
        contexts = {}

        for file_path, content in code_snippets.items():
            contexts[file_path] = self.build_context(file_path, content, code_snippets)

        return contexts


# =============================================================================
# CODE ANALYZER UTILITIES
# =============================================================================

class CodeAnalyzer:
    """Static code analysis utilities."""

    def __init__(self):
        self.patterns = LogPatterns()

    def detect_nested_loops(self, content: str) -> bool:
        """Detect potential nested loops in code."""
        for_count = content.count("for ")
        async_for_count = content.count("async for ")

        # If there are multiple for loops and not all are async
        return for_count > 1 and for_count != async_for_count

    def detect_blocking_calls(self, content: str) -> List[str]:
        """Detect blocking calls in async code."""
        blocking_calls = [
            "time.sleep",
            "requests.get",
            "requests.post",
            "socket.connect",
            "socket.recv",
            "open(",
            "read(",
            "write(",
        ]

        found = []
        for call in blocking_calls:
            if call in content:
                found.append(call)

        return found

    def detect_anti_patterns(self, content: str) -> List[Dict[str, str]]:
        """Detect code anti-patterns."""
        anti_patterns = []

        # Nested loops
        if self.detect_nested_loops(content):
            anti_patterns.append({
                "pattern": "nested_loops",
                "severity": "medium",
                "description": "Multiple sequential for loops detected - potential O(n²)"
            })

        # Blocking calls
        blocking = self.detect_blocking_calls(content)
        if blocking:
            anti_patterns.append({
                "pattern": "blocking_calls",
                "severity": "high",
                "description": f"Blocking calls detected: {', '.join(blocking)}"
            })

        return anti_patterns


# =============================================================================
# TOKEN COUNTER
# =============================================================================

class TokenCounter:
    """Count tokens in text/code."""

    def __init__(self, chars_per_token: int = 4):
        self.chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """Estimate token count from character count."""
        return len(text) // self.chars_per_token

    def count_batch(self, texts: List[str]) -> int:
        """Count tokens for multiple texts."""
        return sum(self.count(text) for text in texts)


# =============================================================================
# TIMING EXTRACTOR
# =============================================================================

class TimingExtractor:
    """Extract timing information from logs."""

    def __init__(self):
        self.ms_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:ms|milliseconds?)", re.IGNORECASE)
        self.s_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(?:s|seconds?)", re.IGNORECASE)

    def extract_ms(self, text: str) -> Optional[float]:
        """Extract timing in milliseconds from text."""
        match = self.ms_pattern.search(text)
        if match:
            return float(match.group(1))

        # Try seconds pattern and convert to ms
        match = self.s_pattern.search(text)
        if match:
            return float(match.group(1)) * 1000

        return None

    def extract_all_timings(self, text: str) -> List[float]:
        """Extract all timing values from text."""
        timings = []

        for match in self.ms_pattern.finditer(text):
            timings.append(float(match.group(1)))

        for match in self.s_pattern.finditer(text):
            timings.append(float(match.group(1)) * 1000)

        return timings
