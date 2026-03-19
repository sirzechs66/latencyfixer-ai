"""
Shared state object for the LatencyFixer AI agent pipeline.

This module defines the AgentState dataclass that maintains context
across all stages of the multi-stage agent workflow.

Note: Uses Pydantic models from agent.models for type consistency.
"""

from typing import List, Dict, Any, Optional
from agent.models import (
    ExtractedEntity,
    DependencyContext,
    RootCause,
    Bottleneck,
    OptimizationFix,
    EvaluationMetrics,
    BenchmarkResult,
    NodeStatus,
)


class AgentState:
    """
    Shared state object passed through all agent pipeline stages.

    This maintains context across the graph-based workflow, allowing
    each node to read and augment the state with its outputs.

    Uses Pydantic models for type validation and serialization.
    """

    def __init__(
        self,
        input_logs: Optional[List[str]] = None,
        code_snippets: Optional[Dict[str, str]] = None,
        system_description: str = "",
    ):
        # Input layer
        self.input_logs = input_logs or []
        self.code_snippets = code_snippets or {}
        self.system_description = system_description

        # Context Retriever outputs
        self.extracted_entities: List[ExtractedEntity] = []
        self.dependency_context: Dict[str, DependencyContext] = {}
        self.context_tokens_total: int = 0
        self.relevant_tokens: int = 0

        # Analyzer outputs
        self.root_causes: List[RootCause] = []
        self.bottlenecks: List[Bottleneck] = []

        # Optimizer outputs
        self.fixes: List[OptimizationFix] = []

        # Evaluator outputs
        self.metrics = EvaluationMetrics()

        # Benchmark outputs
        self.benchmark_results: Optional[BenchmarkResult] = None

        # Execution tracking
        self.node_status: Dict[str, NodeStatus] = {}
        self.execution_log: List[Dict[str, Any]] = []

        # Final report
        self.report_json: Optional[Dict[str, Any]] = None

    def add_log(self, log: str) -> None:
        """Add an input log entry."""
        self.input_logs.append(log)

    def add_code_snippet(self, file_path: str, content: str) -> None:
        """Add a code snippet to the context."""
        self.code_snippets[file_path] = content

    def add_entity(self, entity: ExtractedEntity) -> None:
        """Add an extracted entity."""
        self.extracted_entities.append(entity)

    def add_dependency_context(self, context: DependencyContext) -> None:
        """Add dependency context."""
        self.dependency_context[context.primary_file] = context
        self.relevant_tokens += context.token_count

    def add_root_cause(self, cause: RootCause) -> None:
        """Add a root cause analysis."""
        self.root_causes.append(cause)

    def add_bottleneck(self, bottleneck: Bottleneck) -> None:
        """Add a detected bottleneck."""
        self.bottlenecks.append(bottleneck)

    def add_fix(self, fix: OptimizationFix) -> None:
        """Add an optimization fix suggestion."""
        self.fixes.append(fix)

    def set_node_status(self, node: str, status: NodeStatus) -> None:
        """Set the status of a pipeline node."""
        self.node_status[node] = status

    def log_execution(self, node: str, details: Dict[str, Any]) -> None:
        """Log execution details for a node."""
        self.execution_log.append({
            "node": node,
            "timestamp": details.get("timestamp", ""),
            "status": details.get("status", ""),
            "output": details.get("output", "")
        })

    def get_context_efficiency(self) -> float:
        """Calculate context efficiency score."""
        if self.context_tokens_total == 0:
            return 1.0
        return self.relevant_tokens / self.context_tokens_total

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "input_logs": self.input_logs,
            "code_snippets": self.code_snippets,
            "extracted_entities": [
                e.model_dump() if hasattr(e, "model_dump") else {
                    "entity_type": e.entity_type,
                    "name": e.name,
                    "source": e.source,
                    "line_number": e.line_number,
                    "confidence": e.confidence
                }
                for e in self.extracted_entities
            ],
            "dependency_context": {
                k: {
                    "primary_file": v.primary_file,
                    "content": v.content[:500],
                    "imports": v.imports,
                    "token_count": v.token_count,
                    "depth": v.depth
                }
                for k, v in self.dependency_context.items()
            },
            "root_causes": [
                c.model_dump() if hasattr(c, "model_dump") else {
                    "description": c.description,
                    "category": c.category,
                    "confidence": c.confidence,
                    "evidence": c.evidence,
                    "file_path": c.file_path,
                    "function_name": c.function_name
                }
                for c in self.root_causes
            ],
            "bottlenecks": [
                b.model_dump() if hasattr(b, "model_dump") else {
                    "description": b.description,
                    "location": b.location,
                    "severity": b.severity,
                    "impact_type": b.impact_type,
                    "estimated_impact_ms": b.estimated_impact_ms
                }
                for b in self.bottlenecks
            ],
            "fixes": [
                f.model_dump() if hasattr(f, "model_dump") else {
                    "description": f.description,
                    "fix_type": f.fix_type,
                    "complexity": f.complexity,
                    "expected_latency_improvement_pct": f.expected_latency_improvement_pct,
                    "code_change": f.code_change,
                    "risk_level": f.risk_level
                }
                for f in self.fixes
            ],
            "metrics": self.metrics.model_dump() if hasattr(self.metrics, "model_dump") else {
                "latency_gain": self.metrics.latency_gain,
                "accuracy": self.metrics.accuracy,
                "stability": self.metrics.stability,
                "clarity": self.metrics.clarity,
                "context_efficiency": self.metrics.context_efficiency,
                "final_score": self.metrics.final_score
            },
            "benchmark_results": self.benchmark_results.model_dump() if self.benchmark_results and hasattr(self.benchmark_results, "model_dump") else {
                "agent_score": self.benchmark_results.agent_score if self.benchmark_results else 0,
                "claude_score": self.benchmark_results.claude_score if self.benchmark_results else 0,
                "summary": self.benchmark_results.summary if self.benchmark_results else ""
            } if self.benchmark_results else None,
            "node_status": {k: v.value for k, v in self.node_status.items()}
        }
