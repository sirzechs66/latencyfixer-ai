"""
Optimizer engine for the LatencyFixer AI agent.

This module contains:
- Fix generation from pattern library
- Code change templates
- Latency improvement estimation
"""

from typing import List, Dict, Any

from agent.models import OptimizationFix, RootCause, Bottleneck  # Pydantic models


# =============================================================================
# FIX PATTERN LIBRARY
# =============================================================================

class FixPatternLibrary:
    """Library of optimization fix patterns."""

    FIXES = {
        "io": [
            {
                "description": "Convert blocking I/O to async",
                "fix_type": "async",
                "complexity": "medium",
                "improvement_pct": 40,
            },
            {
                "description": "Implement connection pooling",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 30,
            },
        ],
        "algorithm": [
            {
                "description": "Replace O(n²) with O(n) algorithm",
                "fix_type": "algorithm",
                "complexity": "high",
                "improvement_pct": 80,
            },
            {
                "description": "Add caching/memoization",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 60,
            },
        ],
        "concurrency": [
            {
                "description": "Refactor to async/await",
                "fix_type": "async",
                "complexity": "high",
                "improvement_pct": 50,
            },
            {
                "description": "Add proper locking",
                "fix_type": "async",
                "complexity": "medium",
                "improvement_pct": 35,
            },
        ],
        "compute": [
            {
                "description": "Add memoization for repeated calculations",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 70,
            },
            {
                "description": "Use vectorized operations",
                "fix_type": "algorithm",
                "complexity": "medium",
                "improvement_pct": 60,
            },
        ],
        "memory": [
            {
                "description": "Implement LRU cache with size limit",
                "fix_type": "caching",
                "complexity": "low",
                "improvement_pct": 50,
            },
            {
                "description": "Use generators instead of lists",
                "fix_type": "algorithm",
                "complexity": "low",
                "improvement_pct": 40,
            },
        ],
    }


# =============================================================================
# CODE TEMPLATES
# =============================================================================

class CodeTemplates:
    """Code change templates for common fixes."""

    TEMPLATES = {
        "async_io": """# Before (blocking)
result = requests.get(url)

# After (async)
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        result = await response.text()""",

        "caching": """# Before
def expensive_operation(x):
    return complex_calculation(x)

# After (with caching)
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(x):
    return complex_calculation(x)""",

        "algorithm_replace": """# Before (O(n²))
def find_duplicates(items):
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])

# After (O(n))
def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        else:
            seen.add(item)""",

        "batching": """# Before (N+1 queries)
for user in users:
    orders = db.query("SELECT * FROM orders WHERE user_id = ?", user.id)

# After (batched query)
user_ids = [u.id for u in users]
orders = db.query("SELECT * FROM orders WHERE user_id IN ?", user_ids)""",

        "connection_pool": """# Before (new connection each time)
def query_db(sql):
    conn = create_connection()
    return conn.execute(sql)

# After (connection pooling)
from sqlalchemy import create_engine

engine = create_engine("postgresql://...", pool_size=10, max_overflow=20)

def query_db(sql):
    with engine.connect() as conn:
        return conn.execute(sql)""",
    }

    @classmethod
    def get_template(cls, fix_type: str) -> str:
        """Get code template for a fix type."""
        mapping = {
            "async": cls.TEMPLATES["async_io"],
            "caching": cls.TEMPLATES["caching"],
            "algorithm": cls.TEMPLATES["algorithm_replace"],
            "batching": cls.TEMPLATES["batching"],
        }
        return mapping.get(fix_type, "")


# =============================================================================
# OPTIMIZER ENGINE
# =============================================================================

class OptimizerEngine:
    """Main optimizer engine for generating fix suggestions."""

    def __init__(self):
        self.fix_library = FixPatternLibrary()
        self.templates = CodeTemplates()

    def generate_fixes(
        self,
        root_causes: List[RootCause],
        bottlenecks: List[Bottleneck]
    ) -> List[OptimizationFix]:
        """Generate optimization fixes based on root causes."""
        fixes = []

        # Generate fixes based on root cause categories
        for cause in root_causes:
            category = cause.category

            if category in self.fix_library.FIXES:
                for fix_config in self.fix_library.FIXES[category][:2]:
                    fixes.append(OptimizationFix(
                        description=f"Fix {category} issue: {fix_config['description']}",
                        fix_type=fix_config["fix_type"],
                        complexity=fix_config["complexity"],
                        expected_latency_improvement_pct=(
                            fix_config["improvement_pct"] * cause.confidence
                        ),
                        code_change=self.templates.get_template(fix_config["fix_type"]),
                        risk_level="low" if fix_config["complexity"] == "low" else "medium",
                        effort_estimate=self._get_effort_estimate(fix_config["complexity"])
                    ))

        # Sort by impact/effort ratio
        complexity_weights = {"low": 1, "medium": 2, "high": 3}
        fixes.sort(
            key=lambda f: (
                f.expected_latency_improvement_pct /
                complexity_weights.get(f.complexity, 2)
            ),
            reverse=True
        )

        return fixes

    def _get_effort_estimate(self, complexity: str) -> str:
        """Get effort estimate based on complexity."""
        estimates = {
            "low": "1-2 hours",
            "medium": "4-8 hours",
            "high": "1-3 days",
        }
        return estimates.get(complexity, "unknown")

    def prioritize_fixes(
        self,
        fixes: List[OptimizationFix],
        max_fixes: int = 5
    ) -> List[OptimizationFix]:
        """Prioritize and return top fixes."""
        # Already sorted by impact/effort in generate_fixes
        return fixes[:max_fixes]

    def get_implementation_order(
        self,
        fixes: List[OptimizationFix]
    ) -> List[Dict[str, Any]]:
        """Determine optimal implementation order."""
        order = []

        # Quick wins first (low complexity, high impact)
        quick_wins = [
            f for f in fixes
            if f.complexity == "low" and f.expected_latency_improvement_pct > 30
        ]

        # Then medium complexity
        medium = [
            f for f in fixes
            if f.complexity == "medium"
        ]

        # Finally high complexity
        high = [
            f for f in fixes
            if f.complexity == "high"
        ]

        for phase, fix_list in enumerate([quick_wins, medium, high], 1):
            for fix in fix_list:
                order.append({
                    "fix": fix,
                    "phase": phase,
                    "priority": "high" if phase == 1 else "medium" if phase == 2 else "low"
                })

        return order
