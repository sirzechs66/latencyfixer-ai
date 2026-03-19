"""
Optimizer Node for LatencyFixer AI.

Generates optimization suggestions with estimated latency improvements,
complexity assessments, and code change recommendations.
"""

import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from .state import AgentState, OptimizationFix, RootCause, Bottleneck


class OptimizerNode:
    """
    Optimizer node that generates fix suggestions based on
    identified bottlenecks and root causes.
    """

    # Fix patterns mapped to bottleneck categories
    FIX_PATTERNS = {
        "io": {
            "async_io": {
                "description": "Convert blocking I/O to async operations",
                "fix_type": "async",
                "complexity": "medium",
                "improvement_pct": 40,
                "risk": "medium",
            },
            "connection_pooling": {
                "description": "Implement connection pooling for database/HTTP",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 30,
                "risk": "low",
            },
            "batching": {
                "description": "Batch multiple I/O operations together",
                "fix_type": "batching",
                "complexity": "medium",
                "improvement_pct": 50,
                "risk": "low",
            },
            "buffering": {
                "description": "Add buffering for stream operations",
                "fix_type": "async",
                "complexity": "low",
                "improvement_pct": 25,
                "risk": "low",
            },
        },
        "algorithm": {
            "caching": {
                "description": "Add memoization or caching for repeated computations",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 60,
                "risk": "low",
            },
            "algorithm_replace": {
                "description": "Replace O(n²) algorithm with O(n) or O(n log n)",
                "fix_type": "algorithm",
                "complexity": "high",
                "improvement_pct": 80,
                "risk": "medium",
            },
            "early_exit": {
                "description": "Add early exit conditions to loops",
                "fix_type": "algorithm",
                "complexity": "low",
                "improvement_pct": 20,
                "risk": "low",
            },
            "data_structure": {
                "description": "Use more efficient data structures (set vs list)",
                "fix_type": "algorithm",
                "complexity": "low",
                "improvement_pct": 35,
                "risk": "low",
            },
        },
        "memory": {
            "lazy_loading": {
                "description": "Implement lazy loading for large objects",
                "fix_type": "caching",
                "complexity": "medium",
                "improvement_pct": 30,
                "risk": "low",
            },
            "generator": {
                "description": "Convert list to generator for memory efficiency",
                "fix_type": "algorithm",
                "complexity": "low",
                "improvement_pct": 25,
                "risk": "low",
            },
            "object_pooling": {
                "description": "Implement object pooling to reduce allocations",
                "fix_type": "caching",
                "complexity": "high",
                "improvement_pct": 40,
                "risk": "medium",
            },
        },
        "concurrency": {
            "async_refactor": {
                "description": "Refactor synchronous code to async/await",
                "fix_type": "async",
                "complexity": "high",
                "improvement_pct": 50,
                "risk": "high",
            },
            "lock_optimization": {
                "description": "Reduce lock scope or use lock-free structures",
                "fix_type": "async",
                "complexity": "high",
                "improvement_pct": 35,
                "risk": "medium",
            },
            "parallel_processing": {
                "description": "Process independent tasks in parallel",
                "fix_type": "async",
                "complexity": "medium",
                "improvement_pct": 45,
                "risk": "medium",
            },
            "event_loop": {
                "description": "Fix event loop blocking with run_in_executor",
                "fix_type": "async",
                "complexity": "medium",
                "improvement_pct": 40,
                "risk": "low",
            },
        },
        "compute": {
            "serialization_optimize": {
                "description": "Use faster serialization (orjson vs json)",
                "fix_type": "algorithm",
                "complexity": "low",
                "improvement_pct": 30,
                "risk": "low",
            },
            "precomputation": {
                "description": "Precompute values at startup instead of runtime",
                "fix_type": "caching",
                "complexity": "medium",
                "improvement_pct": 25,
                "risk": "low",
            },
            "vectorization": {
                "description": "Use numpy/vectorized operations for numeric code",
                "fix_type": "algorithm",
                "complexity": "medium",
                "improvement_pct": 70,
                "risk": "low",
            },
        },
    }

    # Code templates for common fixes
    CODE_TEMPLATES = {
        "async_io": """
# Before (blocking)
result = requests.get(url)

# After (async)
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        result = await response.text()
""",
        "caching": """
# Before (repeated computation)
def expensive_operation(x):
    return complex_calculation(x)

# After (with caching)
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(x):
    return complex_calculation(x)
""",
        "generator": """
# Before (memory-intensive list)
def process_items(items):
    results = []
    for item in items:
        results.append(expensive_transform(item))
    return results

# After (memory-efficient generator)
def process_items(items):
    for item in items:
        yield expensive_transform(item)
""",
        "algorithm_replace": """
# Before (O(n²) nested loop)
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates

# After (O(n) with set)
def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)
    return list(duplicates)
""",
        "batching": """
# Before (N+1 queries)
for user_id in user_ids:
    user = db.query("SELECT * FROM users WHERE id = ?", user_id)

# After (batched query)
users = db.query(
    "SELECT * FROM users WHERE id IN (?)",
    user_ids
)
""",
    }

    def __init__(self, prompt_template_path: Optional[str] = None):
        """
        Initialize the optimizer node.

        Args:
            prompt_template_path: Optional path to custom prompt template
        """
        self.template_path = prompt_template_path
        self._load_template()

    def _load_template(self) -> None:
        """Load the optimizer prompt template."""
        default_path = Path(__file__).parent.parent / "prompts" / "optimizer.txt"

        if self.template_path and Path(self.template_path).exists():
            self.template = Path(self.template_path).read_text()
        elif default_path.exists():
            self.template = default_path.read_text()
        else:
            self.template = self._get_default_template()

    def _get_default_template(self) -> str:
        """Return default optimizer prompt template."""
        return """
Generate optimization fixes for the identified bottlenecks.

ANALYSIS RESULTS:
{analysis}

CONTEXT:
{context}

For each bottleneck, suggest:
1. A specific fix with code change if applicable
2. Expected latency improvement percentage
3. Complexity level (low/medium/high)
4. Risk assessment

Output as JSON with fixes[] array.
"""

    def optimize(self, state: AgentState) -> AgentState:
        """
        Generate optimization fixes based on analysis results.

        Args:
            state: Agent state with root causes and bottlenecks

        Returns:
            Updated state with optimization fixes
        """
        # Generate fixes for each bottleneck
        for bottleneck in state.bottlenecks:
            fixes = self._generate_fixes_for_bottleneck(bottleneck, state)
            for fix in fixes:
                state.add_fix(fix)

        # Generate fixes for each root cause
        for cause in state.root_causes:
            fixes = self._generate_fixes_for_cause(cause, state)
            for fix in fixes:
                if not self._is_duplicate_fix(fix, state.fixes):
                    state.add_fix(fix)

        # Prioritize fixes by impact/effort ratio
        state.fixes.sort(
            key=lambda f: f.expected_latency_improvement_pct /
                         ({"low": 1, "medium": 2, "high": 3}[f.complexity]),
            reverse=True
        )

        return state

    def _generate_fixes_for_bottleneck(
        self,
        bottleneck: Bottleneck,
        state: AgentState
    ) -> List[OptimizationFix]:
        """Generate fixes for a specific bottleneck."""
        fixes = []

        # Map severity to urgency
        severity_improvement_bonus = {
            "critical": 1.2,
            "high": 1.1,
            "medium": 1.0,
            "low": 0.9,
        }

        # Find matching fix patterns based on impact type
        if bottleneck.impact_type == "latency":
            # Prioritize async and caching fixes
            fix_candidates = []
            for category_fixes in self.FIX_PATTERNS.values():
                for fix_name, fix_config in category_fixes.items():
                    if fix_config["fix_type"] in ["async", "caching"]:
                        fix_candidates.append((fix_name, fix_config))
        else:
            fix_candidates = []
            for category_fixes in self.FIX_PATTERNS.values():
                for fix_name, fix_config in category_fixes.items():
                    fix_candidates.append((fix_name, fix_config))

        # Generate fixes from candidates
        for fix_name, config in fix_candidates[:3]:  # Top 3 fixes
            fix = OptimizationFix(
                description=config["description"],
                fix_type=config["fix_type"],
                complexity=config["complexity"],
                expected_latency_improvement_pct=config["improvement_pct"] *
                    severity_improvement_bonus.get(bottleneck.severity, 1.0),
                code_change=self.CODE_TEMPLATES.get(fix_name),
                risk_level=config["risk"],
                effort_estimate=self._estimate_effort(config["complexity"])
            )
            fixes.append(fix)

        return fixes

    def _generate_fixes_for_cause(
        self,
        cause: RootCause,
        state: AgentState
    ) -> List[OptimizationFix]:
        """Generate fixes for a specific root cause."""
        fixes = []

        # Get fixes for the cause's category
        if cause.category in self.FIX_PATTERNS:
            category_fixes = self.FIX_PATTERNS[cause.category]

            for fix_name, config in list(category_fixes.items())[:2]:
                fix = OptimizationFix(
                    description=f"Fix {cause.category} issue: {config['description']}",
                    fix_type=config["fix_type"],
                    complexity=config["complexity"],
                    expected_latency_improvement_pct=config["improvement_pct"] *
                        cause.confidence,  # Scale by confidence
                    code_change=self.CODE_TEMPLATES.get(fix_name),
                    risk_level=config["risk"],
                    effort_estimate=self._estimate_effort(config["complexity"])
                )
                fixes.append(fix)

        return fixes

    def _estimate_effort(self, complexity: str) -> str:
        """Estimate effort based on complexity."""
        effort_map = {
            "low": "1-2 hours",
            "medium": "4-8 hours",
            "high": "1-3 days",
        }
        return effort_map.get(complexity, "unknown")

    def _is_duplicate_fix(
        self,
        new_fix: OptimizationFix,
        existing_fixes: List[OptimizationFix]
    ) -> bool:
        """Check if fix is duplicate of existing fix."""
        for existing in existing_fixes:
            if existing.description == new_fix.description:
                return True
            if existing.fix_type == new_fix.fix_type and \
               abs(existing.expected_latency_improvement_pct -
                   new_fix.expected_latency_improvement_pct) < 5:
                return True
        return False

    def get_optimization_summary(self, state: AgentState) -> str:
        """
        Get human-readable optimization summary.

        Args:
            state: Agent state with optimization fixes

        Returns:
            Formatted summary string
        """
        lines = ["=== Optimization Recommendations ===\n"]

        if not state.fixes:
            lines.append("No optimization fixes generated.")
            return "\n".join(lines)

        lines.append(f"Total Fixes: {len(state.fixes)}\n")
        lines.append("Prioritized by Impact/Effort Ratio:\n")

        for i, fix in enumerate(state.fixes, 1):
            lines.append(f"\n{i}. {fix.description}")
            lines.append(f"   Type: {fix.fix_type}")
            lines.append(f"   Complexity: {fix.complexity}")
            lines.append(f"   Expected Improvement: {fix.expected_latency_improvement_pct:.1f}%")
            lines.append(f"   Risk Level: {fix.risk_level}")
            lines.append(f"   Effort: {fix.effort_estimate}")

            if fix.code_change:
                lines.append(f"   Code Change Preview:")
                for code_line in fix.code_change.strip().split("\n")[:5]:
                    lines.append(f"      {code_line}")

        # Calculate total potential improvement
        total_improvement = self._calculate_combined_improvement(state.fixes)
        lines.append(f"\n\n=== Combined Impact ===")
        lines.append(f"Total Potential Improvement: {total_improvement:.1f}%")

        return "\n".join(lines)

    def _calculate_combined_improvement(
        self,
        fixes: List[OptimizationFix]
    ) -> float:
        """
        Calculate combined improvement from all fixes.

        Uses a conservative model where improvements are not fully additive
        due to overlapping effects.
        """
        if not fixes:
            return 0.0

        # Sort by improvement percentage
        sorted_fixes = sorted(
            fixes,
            key=lambda f: f.expected_latency_improvement_pct,
            reverse=True
        )

        # First fix contributes 100% of its improvement
        # Second fix contributes 70% (overlap)
        # Third fix contributes 50%, etc.
        total = 0.0
        contribution_factor = 1.0

        for i, fix in enumerate(sorted_fixes[:5]):  # Top 5 fixes
            if i == 0:
                contribution_factor = 1.0
            elif i == 1:
                contribution_factor = 0.7
            elif i == 2:
                contribution_factor = 0.5
            else:
                contribution_factor = 0.3

            total += fix.expected_latency_improvement_pct * contribution_factor

        return min(total, 95.0)  # Cap at 95%
