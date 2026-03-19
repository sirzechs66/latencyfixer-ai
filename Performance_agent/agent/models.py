# Data models (Pydantic) and lightweight TypedDict for pipeline state.
# I kept models minimal—used by analyzer/evaluator/benchmark components.

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class NodeStatus(Enum):
    """Status of each node in the pipeline."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(Enum):
    """Severity levels for bottlenecks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FixType(Enum):
    """Types of optimization fixes."""
    ALGORITHM = "algorithm"
    CACHING = "caching"
    ASYNC = "async"
    BATCHING = "batching"
    QUERY = "query"


class RootCauseCategory(Enum):
    """Categories for root cause analysis."""
    IO = "io"
    COMPUTE = "compute"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    ALGORITHM = "algorithm"


# =============================================================================
# PYDANTIC MODELS (for agent state)
# =============================================================================

class ExtractedEntity(BaseModel):
    """Represents an entity extracted from logs/stack traces."""
    entity_type: str  # "file", "function", "module", "class"
    name: str
    source: str  # which log/trace it came from
    line_number: Optional[int] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DependencyContext(BaseModel):
    """Represents retrieved dependency context."""
    primary_file: str
    content: str
    imports: List[str] = Field(default_factory=list)
    related_functions: List[Dict[str, str]] = Field(default_factory=list)
    token_count: int = Field(default=0, ge=0)
    depth: int = Field(default=0, ge=0)


class RootCause(BaseModel):
    """Represents an identified root cause."""
    description: str
    category: str  # "io", "compute", "memory", "concurrency", "algorithm"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: List[str]
    file_path: Optional[str] = None
    function_name: Optional[str] = None


class Bottleneck(BaseModel):
    """Represents a detected performance bottleneck."""
    description: str
    location: str
    severity: str  # "low", "medium", "high", "critical"
    impact_type: str  # "latency", "throughput", "memory", "cpu"
    estimated_impact_ms: float = Field(default=0.0, ge=0.0)


class OptimizationFix(BaseModel):
    """Represents a suggested optimization."""
    description: str
    fix_type: str  # "algorithm", "caching", "async", "batching"
    complexity: str  # "low", "medium", "high"
    expected_latency_improvement_pct: float = Field(ge=0.0, le=100.0)
    code_change: Optional[str] = None
    risk_level: str = Field(default="low", pattern="^(low|medium|high)$")
    effort_estimate: str = "hours"


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for the output."""
    latency_gain: float = Field(default=0.0, ge=0.0, le=1.0)
    accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    stability: float = Field(default=0.0, ge=0.0, le=1.0)
    clarity: float = Field(default=0.0, ge=0.0, le=1.0)
    context_efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    final_score: float = Field(default=0.0, ge=0.0, le=10000.0)


class BenchmarkResult(BaseModel):
    """Benchmark comparison results."""
    agent_score: float
    claude_score: float
    agent_structure: float = Field(default=0.0)
    claude_structure: float = Field(default=0.0)
    agent_quantification: float = Field(default=0.0)
    claude_quantification: float = Field(default=0.0)
    agent_depth: float = Field(default=0.0)
    claude_depth: float = Field(default=0.0)
    agent_efficiency: float = Field(default=0.0)
    claude_efficiency: float = Field(default=0.0)
    summary: str = ""


# =============================================================================
# TYPED DICT (for LangGraph state)
# =============================================================================

class LatencyFixerState(TypedDict, total=False):
    """
    State schema for the LatencyFixer AI pipeline.

    Uses LangGraph's TypedDict pattern for state updates.
    """
    # Input layer
    input_logs: List[str]
    code_snippets: Dict[str, str]
    system_description: str

    # Context Retriever outputs
    extracted_entities: List[Dict[str, Any]]
    dependency_context: Dict[str, Dict[str, Any]]
    context_tokens_total: int
    relevant_tokens: int

    # Analyzer outputs
    root_causes: List[Dict[str, Any]]
    bottlenecks: List[Dict[str, Any]]

    # Optimizer outputs
    fixes: List[Dict[str, Any]]

    # Evaluator outputs
    metrics: Dict[str, float]
    final_score: float

    # Benchmark outputs
    benchmark_results: Dict[str, Any]

    # Execution tracking
    node_status: Dict[str, str]
    execution_log: List[Dict[str, Any]]

    # Final report
    report_json: Dict[str, Any]
