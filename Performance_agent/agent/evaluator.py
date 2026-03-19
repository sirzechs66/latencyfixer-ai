"""
Evaluator Node for LatencyFixer AI.

Evaluates the output quality across 5 dimensions and calculates
the final score (1-10,000 scale).
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from .state import AgentState, EvaluationMetrics


class EvaluatorNode:
    """
    Evaluator node that scores the agent output on:
    - Latency Gain (35% weight)
    - Accuracy (25% weight)
    - Stability (15% weight)
    - Clarity (15% weight)
    - Context Efficiency (10% weight)

    Final Score = weighted_sum * 10000
    """

    # Scoring weights
    WEIGHTS = {
        "latency_gain": 0.35,
        "accuracy": 0.25,
        "stability": 0.15,
        "clarity": 0.15,
        "context_efficiency": 0.10,
    }

    def __init__(self, prompt_template_path: Optional[str] = None):
        """
        Initialize the evaluator node.

        Args:
            prompt_template_path: Optional path to custom prompt template
        """
        self.template_path = prompt_template_path
        self._load_template()

    def _load_template(self) -> None:
        """Load the evaluator prompt template."""
        default_path = Path(__file__).parent.parent / "prompts" / "evaluator.txt"

        if self.template_path and Path(self.template_path).exists():
            self.template = Path(self.template_path).read_text()
        elif default_path.exists():
            self.template = default_path.read_text()
        else:
            self.template = self._get_default_template()

    def _get_default_template(self) -> str:
        """Return default evaluator prompt template."""
        return """
Evaluate the quality of the latency analysis output.

ANALYSIS RESULTS:
{analysis}

FIXES PROPOSED:
{fixes}

CONTEXT USED:
{context}

Score each dimension (0-1):
1. Latency Gain - expected improvement from fixes
2. Accuracy - confidence in root cause identification
3. Stability - risk level of proposed fixes
4. Clarity - specificity and actionability of findings
5. Context Efficiency - relevant tokens / total tokens

Final Score = weighted_sum * 10000
"""

    def evaluate(self, state: AgentState) -> AgentState:
        """
        Evaluate the agent output and calculate final score.

        Args:
            state: Agent state with complete analysis results

        Returns:
            Updated state with evaluation metrics and final score
        """
        # Calculate each dimension
        latency_gain = self._score_latency_gain(state)
        accuracy = self._score_accuracy(state)
        stability = self._score_stability(state)
        clarity = self._score_clarity(state)
        context_efficiency = state.get_context_efficiency()

        # Calculate weighted score
        weighted_score = (
            latency_gain * self.WEIGHTS["latency_gain"] +
            accuracy * self.WEIGHTS["accuracy"] +
            stability * self.WEIGHTS["stability"] +
            clarity * self.WEIGHTS["clarity"] +
            context_efficiency * self.WEIGHTS["context_efficiency"]
        )

        # Scale to 1-10,000
        final_score = weighted_score * 10000

        # Store metrics
        state.metrics = EvaluationMetrics(
            latency_gain=latency_gain,
            accuracy=accuracy,
            stability=stability,
            clarity=clarity,
            context_efficiency=context_efficiency,
            final_score=final_score
        )

        return state

    def _score_latency_gain(self, state: AgentState) -> float:
        """
        Score latency gain potential from proposed fixes.

        Based on:
        - Expected improvement percentages from fixes
        - Number of bottlenecks addressed
        - Severity of addressed bottlenecks

        Returns:
            Normalized score 0-1
        """
        if not state.fixes:
            return 0.0

        # Calculate weighted improvement score
        total_improvement = 0.0
        severity_weights = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
        }

        # Sum improvements weighted by severity of addressed bottlenecks
        for i, fix in enumerate(state.fixes[:5]):  # Top 5 fixes
            # Find corresponding bottleneck severity
            severity = "medium"  # Default
            if i < len(state.bottlenecks):
                severity = state.bottlenecks[i].severity

            weight = severity_weights.get(severity, 0.5)
            total_improvement += fix.expected_latency_improvement_pct * weight

        # Normalize: 50% improvement = 1.0 score
        # Cap at 100% for normalization
        normalized = min(total_improvement / 50.0, 1.0)

        return normalized

    def _score_accuracy(self, state: AgentState) -> float:
        """
        Score accuracy of root cause identification.

        Based on:
        - Confidence scores of root causes
        - Evidence quality
        - Specificity of findings

        Returns:
            Normalized score 0-1
        """
        if not state.root_causes:
            return 0.0

        # Average confidence of root causes
        avg_confidence = sum(
            c.confidence for c in state.root_causes
        ) / len(state.root_causes)

        # Evidence bonus: more evidence = higher accuracy
        evidence_bonus = 0.0
        for cause in state.root_causes:
            if len(cause.evidence) >= 3:
                evidence_bonus += 0.1
            elif len(cause.evidence) >= 1:
                evidence_bonus += 0.05

        # File specificity bonus
        file_bonus = 0.0
        for cause in state.root_causes:
            if cause.file_path:
                file_bonus += 0.05

        # Combine scores (cap at 1.0)
        accuracy = min(avg_confidence + evidence_bonus + file_bonus, 1.0)

        return accuracy

    def _score_stability(self, state: AgentState) -> float:
        """
        Score stability/risk of proposed fixes.

        Based on:
        - Risk levels of fixes
        - Complexity levels
        - Conservative vs aggressive changes

        Returns:
            Normalized score 0-1 (higher = more stable/safer)
        """
        if not state.fixes:
            return 0.5  # Neutral if no fixes

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

        # Average risk and complexity scores
        avg_risk = sum(
            risk_scores.get(f.risk_level, 0.5) for f in state.fixes
        ) / len(state.fixes)

        avg_complexity = sum(
            complexity_scores.get(f.complexity, 0.5) for f in state.fixes
        ) / len(state.fixes)

        # Stability is weighted average of risk and complexity
        stability = (avg_risk * 0.6) + (avg_complexity * 0.4)

        return stability

    def _score_clarity(self, state: AgentState) -> float:
        """
        Score clarity of findings and recommendations.

        Based on:
        - Specificity of descriptions
        - Quantification of impact
        - Actionability of fixes
        - Structure of output

        Returns:
            Normalized score 0-1
        """
        clarity_score = 0.0

        # Root cause clarity
        if state.root_causes:
            for cause in state.root_causes:
                # Specific description (not vague)
                if len(cause.description) > 20:
                    clarity_score += 0.1
                # Has file location
                if cause.file_path:
                    clarity_score += 0.1
                # Has function location
                if cause.function_name:
                    clarity_score += 0.05
                # Has evidence
                if cause.evidence:
                    clarity_score += 0.05

        # Bottleneck clarity
        if state.bottlenecks:
            for bottleneck in state.bottlenecks:
                # Has quantified impact
                if bottleneck.estimated_impact_ms > 0:
                    clarity_score += 0.1
                # Has severity classification
                if bottleneck.severity in ["critical", "high", "medium", "low"]:
                    clarity_score += 0.05
                # Has impact type
                if bottleneck.impact_type:
                    clarity_score += 0.05

        # Fix clarity
        if state.fixes:
            for fix in state.fixes:
                # Has code change
                if fix.code_change:
                    clarity_score += 0.1
                # Has effort estimate
                if fix.effort_estimate:
                    clarity_score += 0.05
                # Has quantified improvement
                if fix.expected_latency_improvement_pct > 0:
                    clarity_score += 0.05

        # Normalize to 0-1 (cap at 15 checkpoints = 1.0)
        clarity_score = min(clarity_score / 1.5, 1.0)

        return clarity_score

    def get_evaluation_summary(self, state: AgentState) -> str:
        """
        Get human-readable evaluation summary.

        Args:
            state: Agent state with evaluation metrics

        Returns:
            Formatted summary string
        """
        lines = ["=== Evaluation Results ===\n"]

        lines.append("Dimension Scores (0-1 scale):")
        lines.append(f"  Latency Gain:      {state.metrics.latency_gain:.3f}")
        lines.append(f"  Accuracy:          {state.metrics.accuracy:.3f}")
        lines.append(f"  Stability:         {state.metrics.stability:.3f}")
        lines.append(f"  Clarity:           {state.metrics.clarity:.3f}")
        lines.append(f"  Context Efficiency:{state.metrics.context_efficiency:.3f}")

        lines.append(f"\nWeights:")
        for dim, weight in self.WEIGHTS.items():
            lines.append(f"  {dim}: {weight:.0%}")

        lines.append(f"\n=== FINAL SCORE ===")
        lines.append(f"Score: {state.metrics.final_score:.0f} / 10,000")

        # Rating interpretation
        score_rating = self._interpret_score(state.metrics.final_score)
        lines.append(f"Rating: {score_rating}")

        return "\n".join(lines)

    def _interpret_score(self, score: float) -> str:
        """Interpret the final score."""
        if score >= 8500:
            return "Excellent - Production ready"
        elif score >= 7000:
            return "Very Good - Minor improvements possible"
        elif score >= 5500:
            return "Good - Solid analysis with room for enhancement"
        elif score >= 4000:
            return "Fair - Adequate but needs refinement"
        elif score >= 2500:
            return "Below Average - Significant improvements needed"
        else:
            return "Poor - Major rework required"
