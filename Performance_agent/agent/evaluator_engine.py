# Evaluator engine — minimal human-style notes:
# I added the evaluator logic that combines latency/accuracy/stability into a
# single final score. Kept scoring helpers compact and readable.

from typing import List, Dict, Any

from agent.models import EvaluationMetrics, RootCause, Bottleneck, OptimizationFix  # Pydantic models


# Scoring configuration (weights and thresholds)

class ScoringConfig:
    """Scoring weights and thresholds."""

    WEIGHTS = {
        "latency_gain": 0.35,
        "accuracy": 0.25,
        "stability": 0.15,
        "clarity": 0.15,
        "context_efficiency": 0.10,
    }

    SEVERITY_WEIGHTS = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4,
    }

    RISK_SCORES = {
        "low": 1.0,
        "medium": 0.6,
        "high": 0.3,
    }

    COMPLEXITY_SCORES = {
        "low": 1.0,
        "medium": 0.7,
        "high": 0.4,
    }

    @classmethod
    def get_rating(cls, score: float) -> str:
        """Get rating label based on score."""
        if score >= 8500:
            return "Excellent - Production ready"
        elif score >= 7000:
            return "Very Good"
        elif score >= 5500:
            return "Good"
        elif score >= 4000:
            return "Fair"
        elif score >= 2500:
            return "Below Average"
        else:
            return "Poor"


# Evaluator engine implementation

class EvaluatorEngine:
    """Main evaluator engine for scoring analysis quality."""

    def __init__(self):
        self.config = ScoringConfig()

    def evaluate(
        self,
        fixes: List[dict],
        root_causes: List[dict],
        bottlenecks: List[dict],
        relevant_tokens: int,
        total_tokens: int,
        logs: str = "",
        expected_focus: str = None,
        expected_issue: str = None
    ) -> dict:
        """Evaluate analysis quality across 5 dimensions with input variability."""
        # Normalize inputs: allow Pydantic models or dicts
        fixes_list = [f.dict() if hasattr(f, "dict") else f for f in (fixes or [])]
        root_causes_list = [rc.dict() if hasattr(rc, "dict") else rc for rc in (root_causes or [])]
        bottlenecks_list = [bn.dict() if hasattr(bn, "dict") else bn for bn in (bottlenecks or [])]
        # 1. Latency Gain: parse logs for ms delays, normalize
        latency_gain = self._score_latency_gain_variable(fixes_list, bottlenecks_list, logs, expected_focus)
        # 2. Accuracy: compare detected issue vs expected
        accuracy = self._score_accuracy_variable(root_causes_list, expected_issue)
        # 3. Stability: lower for high risk/complexity
        stability = self._score_stability(fixes_list)
        # 4. Clarity: check output structure
        clarity = self._score_clarity(root_causes_list, bottlenecks_list, fixes_list)
        # 5. Context Efficiency: relevant/total tokens
        context_efficiency = self._score_context_efficiency(relevant_tokens, total_tokens)

        # Problem-type adjustment: weight latency contribution based on expected focus
        if expected_focus == "algorithm":
            latency_gain = min(latency_gain * 0.7, 1.0)
        elif expected_focus == "latency":
            latency_gain = min(latency_gain * 1.1, 1.0)

        # Clamp all metric values into [0,1]
        latency_gain = max(0.0, min(latency_gain, 1.0))
        accuracy = max(0.0, min(accuracy, 1.0))
        stability = max(0.0, min(stability, 1.0))
        clarity = max(0.0, min(clarity, 1.0))
        context_efficiency = max(0.0, min(context_efficiency, 1.0))

        # New scoring behavior requested:
        # - Scale each metric to a 0..10000 range individually
        # - If at least 2 of the 3 primary tests (latency_gain, accuracy, stability)
        #   are present (non-zero), compute final_score as the average of those
        #   scaled values. Otherwise, average all available scaled metrics.

        metrics = {
            "latency_gain": latency_gain,
            "accuracy": accuracy,
            "stability": stability,
            "clarity": clarity,
            "context_efficiency": context_efficiency,
        }

        # Scale each metric to 0..10000
        scaled = {k: int(max(0.0, min(v, 1.0)) * 10000) for k, v in metrics.items()}

        primary_keys = ["latency_gain", "accuracy", "stability"]
        present_primary = [scaled[k] for k in primary_keys if metrics.get(k, 0) > 0]

        if len(present_primary) >= 2:
            final_score = int(sum(present_primary) / len(present_primary))
        else:
            # Fallback: average all metrics that were computed (use all keys)
            present_all = [v for k, v in scaled.items() if metrics.get(k, 0) >= 0]
            final_score = int(sum(present_all) / max(len(present_all), 1))

        final_score = max(0, min(final_score, 10000))

        return {
            "latency_gain": round(latency_gain, 3),
            "accuracy": round(accuracy, 3),
            "stability": round(stability, 3),
            "clarity": round(clarity, 3),
            "context_efficiency": round(context_efficiency, 3),
            "final_score": final_score,
            "metrics_scaled": scaled,
        }

    def _score_latency_gain_variable(self, fixes, bottlenecks, logs, expected_focus):
        # If expected_focus is latency, parse logs for ms delays
        import re
        ms_values = [int(x) for x in re.findall(r"(\d+)ms", logs)] if logs else []
        max_ms = max(ms_values) if ms_values else 0
        # If explicit latency focus, use smooth normalization
        if expected_focus == "latency":
            return self._normalize_latency(max_ms)
        # Otherwise, fallback to fix-based
        return self._score_latency_gain(fixes, bottlenecks)

    def _normalize_latency(self, ms: int) -> float:
        """Smoothly normalize latency ms into [0.2, 1.0]."""
        if ms <= 100:
            return 1.0
        if ms >= 3000:
            return 0.4
        # smoother decay across 0-3000ms but with softer floor
        return max(0.4, 1.0 - (ms / 5000))

    def _score_accuracy_variable(self, root_causes, expected_issue):
        # If expected_issue is provided, compare to root cause categories
        if expected_issue:
            categories = [rc.get("category") for rc in root_causes]
            return self._match_score(expected_issue, categories)
        return self._score_accuracy(root_causes)

    def _match_score(self, expected: str, detected: list) -> float:
        """Return a partial/semantic match score between expected and detected categories."""
        if not expected or not detected:
            return 0.3

        expected = expected.lower()
        detected_text = " ".join([d or "" for d in detected]).lower()

        if expected in detected_text:
            return 0.9
        if any(word in detected_text for word in expected.split()):
            return 0.7
        return 0.5

    def _score_latency_gain(
        self,
        fixes: List[dict],
        bottlenecks: List[dict]
    ) -> float:
        """
        Score latency gain (35%).
        Based on expected improvement from fixes and severity coverage.
        """
        score = 0.0

        for i, fix in enumerate(fixes[:5]):
            severity = (
                bottlenecks[i].get("severity")
                if i < len(bottlenecks)
                else "medium"
            )
            weight = self.config.SEVERITY_WEIGHTS.get(severity, 0.5)
            score += fix.get("expected_latency_improvement_pct", 0) * weight

        return min(score / 50.0, 1.0)

    def _score_accuracy(self, root_causes: List[dict]) -> float:
        """
        Score accuracy (25%).
        Based on confidence scores, evidence quality, and specificity.
        """
        if not root_causes:
            return 0.0

        avg_confidence = sum(rc.get("confidence", 0.5) for rc in root_causes) / len(root_causes)

        # Evidence bonus
        evidence_bonus = sum(
            0.1 if len(rc.get("evidence", [])) >= 3 else 0.05
            for rc in root_causes
        )

        # Location bonus
        location_bonus = sum(
            0.05 if rc.get("file_path") else 0
            for rc in root_causes
        )

        return min(avg_confidence + evidence_bonus + location_bonus, 1.0)

    def _score_stability(self, fixes: List[OptimizationFix]) -> float:
        """
        Score stability (15%).
        Based on risk levels and complexity of proposed fixes.
        """
        if not fixes:
            return 0.5

        avg_risk = sum(
            self.config.RISK_SCORES.get(f.get("risk_level", "medium"), 0.5)
            for f in fixes
        ) / len(fixes)

        avg_complexity = sum(
            self.config.COMPLEXITY_SCORES.get(f.get("complexity", "medium"), 0.5)
            for f in fixes
        ) / len(fixes)

        return (avg_risk * 0.6) + (avg_complexity * 0.4)

    def _score_clarity(
        self,
        root_causes: List[dict],
        bottlenecks: List[dict],
        fixes: List[dict]
    ) -> float:
        """
        Score clarity (15%).
        Based on specificity, quantification, and actionability.
        """
        score = 0.0

        # Root cause clarity
        for rc in root_causes:
            if len(rc.get("description", "")) > 20:
                score += 0.1
            if rc.get("file_path"):
                score += 0.1
            if rc.get("evidence"):
                score += 0.05

        # Bottleneck clarity
        for bn in bottlenecks:
            if bn.get("estimated_impact_ms", 0) > 0:
                score += 0.1
            if bn.get("severity"):
                score += 0.05

        # Fix clarity
        for fix in fixes:
            if fix.get("code_change"):
                score += 0.1
            if fix.get("expected_latency_improvement_pct", 0) > 0:
                score += 0.05

        # Normalize clarity by total number of items to avoid inflation
        denominator = len(root_causes) + len(bottlenecks) + len(fixes) + 1
        return min(score / max(denominator, 1), 1.0)

    def _score_context_efficiency(
        self,
        relevant_tokens: int,
        total_tokens: int
    ) -> float:
        """
        Score context efficiency (10%).
        Ratio of relevant tokens to total tokens.
        """
        if total_tokens == 0:
            return 1.0
        return min(relevant_tokens / max(total_tokens, 1), 1.0)

    def _calculate_final_score(
        self,
        latency_gain: float,
        accuracy: float,
        stability: float,
        clarity: float,
        context_efficiency: float
    ) -> float:
        """Calculate weighted final score (1-10,000 scale)."""
        return (
            latency_gain * self.config.WEIGHTS["latency_gain"] +
            accuracy * self.config.WEIGHTS["accuracy"] +
            stability * self.config.WEIGHTS["stability"] +
            clarity * self.config.WEIGHTS["clarity"] +
            context_efficiency * self.config.WEIGHTS["context_efficiency"]
        ) * 10000

    def get_rating(self, score: float) -> str:
        """Get rating label for a score."""
        return self.config.get_rating(score)

    def generate_score_breakdown(
        self,
        metrics: EvaluationMetrics
    ) -> Dict[str, Any]:
        """Generate detailed score breakdown."""
        return {
            "dimensions": {
                "latency_gain": {
                    "score": metrics.latency_gain,
                    "weight": self.config.WEIGHTS["latency_gain"],
                    "contribution": metrics.latency_gain * self.config.WEIGHTS["latency_gain"]
                },
                "accuracy": {
                    "score": metrics.accuracy,
                    "weight": self.config.WEIGHTS["accuracy"],
                    "contribution": metrics.accuracy * self.config.WEIGHTS["accuracy"]
                },
                "stability": {
                    "score": metrics.stability,
                    "weight": self.config.WEIGHTS["stability"],
                    "contribution": metrics.stability * self.config.WEIGHTS["stability"]
                },
                "clarity": {
                    "score": metrics.clarity,
                    "weight": self.config.WEIGHTS["clarity"],
                    "contribution": metrics.clarity * self.config.WEIGHTS["clarity"]
                },
                "context_efficiency": {
                    "score": metrics.context_efficiency,
                    "weight": self.config.WEIGHTS["context_efficiency"],
                    "contribution": metrics.context_efficiency * self.config.WEIGHTS["context_efficiency"]
                },
            },
            "final_score": metrics.final_score,
            "rating": self.get_rating(metrics.final_score)
        }
