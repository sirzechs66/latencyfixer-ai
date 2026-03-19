"""
Scoring Engine for LatencyFixer AI.

Core scoring formulas and utilities for the 1-10,000 scale evaluation system.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of score components."""
    latency_gain: float
    accuracy: float
    stability: float
    clarity: float
    context_efficiency: float
    weighted_sum: float
    final_score: float


class ScoringEngine:
    """
    Calculates scores using the weighted formula:

    Score = (
        latency_gain * 0.35 +
        accuracy * 0.25 +
        stability * 0.15 +
        clarity * 0.15 +
        context_efficiency * 0.10
    ) * 10000

    All metrics normalized to [0, 1].
    """

    WEIGHTS = {
        "latency_gain": 0.35,
        "accuracy": 0.25,
        "stability": 0.15,
        "clarity": 0.15,
        "context_efficiency": 0.10,
    }

    SCORE_RATINGS = {
        (8500, 10000): "Excellent - Production ready",
        (7000, 8499): "Very Good - Minor improvements possible",
        (5500, 6999): "Good - Solid analysis with room for enhancement",
        (4000, 5499): "Fair - Adequate but needs refinement",
        (2500, 3999): "Below Average - Significant improvements needed",
        (0, 2499): "Poor - Major rework required",
    }

    def calculate_score(
        self,
        metrics: Dict[str, float]
    ) -> ScoreBreakdown:
        """
        Calculate final score from normalized metrics.

        Args:
            metrics: Dictionary with metric names and values (0-1 scale)

        Returns:
            ScoreBreakdown with all components and final score
        """
        # Ensure all metrics are in [0, 1]
        normalized = {
            k: max(0.0, min(1.0, v))
            for k, v in metrics.items()
        }

        # Calculate weighted sum
        weighted_sum = sum(
            normalized.get(k, 0.0) * weight
            for k, weight in self.WEIGHTS.items()
        )

        # Scale to 1-10,000
        final_score = weighted_sum * 10000

        return ScoreBreakdown(
            latency_gain=normalized.get("latency_gain", 0.0),
            accuracy=normalized.get("accuracy", 0.0),
            stability=normalized.get("stability", 0.0),
            clarity=normalized.get("clarity", 0.0),
            context_efficiency=normalized.get("context_efficiency", 0.0),
            weighted_sum=weighted_sum,
            final_score=final_score
        )

    def calculate_latency_gain(
        self,
        fixes: List[Dict[str, Any]],
        bottlenecks: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate latency gain score from fixes and bottlenecks.

        Args:
            fixes: List of fix dictionaries with expected_latency_improvement_pct
            bottlenecks: List of bottleneck dictionaries with severity

        Returns:
            Normalized latency gain score (0-1)
        """
        if not fixes:
            return 0.0

        severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
        }

        total_weighted_improvement = 0.0

        for i, fix in enumerate(fixes[:5]):
            improvement = fix.get("expected_latency_improvement_pct", 0)

            # Get severity from corresponding bottleneck
            severity = "medium"
            if i < len(bottlenecks):
                severity = bottlenecks[i].get("severity", "medium")

            weight = severity_weights.get(severity, 0.5)
            total_weighted_improvement += improvement * weight

        # Normalize: 50% = 1.0 score
        return min(total_weighted_improvement / 50.0, 1.0)

    def calculate_accuracy(
        self,
        root_causes: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate accuracy score from root cause analysis.

        Args:
            root_causes: List of root cause dictionaries

        Returns:
            Normalized accuracy score (0-1)
        """
        if not root_causes:
            return 0.0

        # Average confidence
        confidences = [
            rc.get("confidence", 0.5)
            for rc in root_causes
        ]
        avg_confidence = sum(confidences) / len(confidences)

        # Evidence bonus
        evidence_bonus = 0.0
        for rc in root_causes:
            evidence = rc.get("evidence", [])
            if len(evidence) >= 3:
                evidence_bonus += 0.1
            elif len(evidence) >= 1:
                evidence_bonus += 0.05

        # Location specificity bonus
        location_bonus = 0.0
        for rc in root_causes:
            if rc.get("file_path"):
                location_bonus += 0.05
            if rc.get("function_name"):
                location_bonus += 0.05

        return min(avg_confidence + evidence_bonus + location_bonus, 1.0)

    def calculate_stability(
        self,
        fixes: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate stability score from fix risk levels.

        Args:
            fixes: List of fix dictionaries with risk_level and complexity

        Returns:
            Normalized stability score (0-1)
        """
        if not fixes:
            return 0.5

        risk_scores = {
            "low": 1.0,
            "medium": 0.6,
            "high": 0.3,
        }

        complexity_scores = {
            "low": 1.0,
            "medium": 0.7,
            "high": 0.4,
        }

        avg_risk = sum(
            risk_scores.get(f.get("risk_level", "medium"), 0.5)
            for f in fixes
        ) / len(fixes)

        avg_complexity = sum(
            complexity_scores.get(f.get("complexity", "medium"), 0.5)
            for f in fixes
        ) / len(fixes)

        return (avg_risk * 0.6) + (avg_complexity * 0.4)

    def calculate_clarity(
        self,
        root_causes: List[Dict[str, Any]],
        bottlenecks: List[Dict[str, Any]],
        fixes: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate clarity score from output quality.

        Args:
            root_causes: List of root cause dictionaries
            bottlenecks: List of bottleneck dictionaries
            fixes: List of fix dictionaries

        Returns:
            Normalized clarity score (0-1)
        """
        clarity_score = 0.0

        # Root cause clarity
        for rc in root_causes:
            if len(rc.get("description", "")) > 20:
                clarity_score += 0.1
            if rc.get("file_path"):
                clarity_score += 0.1
            if rc.get("function_name"):
                clarity_score += 0.05
            if rc.get("evidence"):
                clarity_score += 0.05

        # Bottleneck clarity
        for bn in bottlenecks:
            if bn.get("estimated_impact_ms", 0) > 0:
                clarity_score += 0.1
            if bn.get("severity") in ["critical", "high", "medium", "low"]:
                clarity_score += 0.05
            if bn.get("impact_type"):
                clarity_score += 0.05

        # Fix clarity
        for fix in fixes:
            if fix.get("code_change"):
                clarity_score += 0.1
            if fix.get("effort_estimate"):
                clarity_score += 0.05
            if fix.get("expected_latency_improvement_pct", 0) > 0:
                clarity_score += 0.05

        return min(clarity_score / 1.5, 1.0)

    def calculate_context_efficiency(
        self,
        relevant_tokens: int,
        total_tokens: int
    ) -> float:
        """
        Calculate context efficiency score.

        Args:
            relevant_tokens: Number of relevant tokens used
            total_tokens: Total tokens in context

        Returns:
            Ratio of relevant/total (0-1)
        """
        if total_tokens == 0:
            return 1.0

        return relevant_tokens / total_tokens

    def get_rating(self, score: float) -> str:
        """
        Get rating description for a score.

        Args:
            score: Final score (0-10000)

        Returns:
            Rating string
        """
        for (min_score, max_score), rating in sorted(
            self.SCORE_RATINGS.items(),
            key=lambda x: x[0][0],
            reverse=True
        ):
            if min_score <= score <= max_score:
                return rating

        return "Unknown rating"

    def get_grade(self, score: float) -> str:
        """
        Get letter grade for a score.

        Args:
            score: Final score (0-10000)

        Returns:
            Letter grade (A, B, C, D, F)
        """
        if score >= 8500:
            return "A"
        elif score >= 7000:
            return "B"
        elif score >= 5500:
            return "C"
        elif score >= 4000:
            return "D"
        else:
            return "F"

    def compare_scores(
        self,
        score_a: ScoreBreakdown,
        score_b: ScoreBreakdown
    ) -> Dict[str, Any]:
        """
        Compare two score breakdowns.

        Args:
            score_a: First score breakdown
            score_b: Second score breakdown

        Returns:
            Comparison dictionary
        """
        diff = score_a.final_score - score_b.final_score

        return {
            "score_a": score_a.final_score,
            "score_b": score_b.final_score,
            "difference": diff,
            "winner": "A" if diff > 0 else ("B" if diff < 0 else "Tie"),
            "dimension_comparison": {
                "latency_gain": score_a.latency_gain - score_b.latency_gain,
                "accuracy": score_a.accuracy - score_b.accuracy,
                "stability": score_a.stability - score_b.stability,
                "clarity": score_a.clarity - score_b.clarity,
                "context_efficiency": score_a.context_efficiency - score_b.context_efficiency,
            }
        }
