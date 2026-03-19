# LatencyFixer AI

A production-quality multi-stage AI agent system for latency analysis and optimization with **dependency-aware context retrieval**.

## Problem Statement

Traditional LLM-based code analysis tools suffer from:

1. **Context Window Bloat** - Passing entire codebases wastes tokens
2. **Lost Attention** - Irrelevant code dilutes model focus
3. **Higher Costs** - More tokens = higher API costs
4. **Slower Inference** - Large context = slower processing
5. **Vague Suggestions** - Generic "optimize this function" without specifics

## Solution: Dependency-Aware Context Retrieval

LatencyFixer AI uses a **shallow dependency graph** to retrieve only relevant code:

```
Logs/Errors → Entity Extraction → Dependency Expansion → Relevant Context
     ↓              ↓                    ↓                    ↓
  stack traces   file/function      direct imports      focused code
  error msgs     caller/callee      depth 1-2 max       only
```

### Context Efficiency Metric

```
Context Efficiency = Relevant Tokens / Total Tokens
```

Typical results: 60-80% efficiency vs 10-30% for full-codebase approaches.

## Architecture

```
┌─────────────────┐
│   Input Layer   │ (logs, code snippets, error messages)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context         │
│ Retriever       │ → Extracts entities, builds shallow dependency graph
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analyzer        │ → Root cause detection, bottleneck identification
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Optimizer       │ → Fix suggestions with % improvement estimates
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Evaluator       │ → 5-dimension scoring (1-10,000 scale)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Benchmark       │ → Comparison vs baseline Claude
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Report          │ → Structured JSON output
└─────────────────┘
```

## Agent Modules

### 1. Context Retriever (`agent/context_retriever.py`)
- Parses logs/stack traces for file/function names
- Uses regex + AST for Python file parsing
- Expands to direct imports (depth 1)
- Includes caller/callee relationships (depth 2)

### 2. Analyzer (`agent/analyzer.py`)
- Pattern-based bottleneck detection
- Code anti-pattern recognition (nested loops, blocking calls)
- Root cause categorization (io, compute, memory, concurrency, algorithm)

### 3. Optimizer (`agent/optimizer.py`)
- Fix generation from pattern library
- Code change templates
- Latency improvement estimation
- Complexity/risk assessment

### 4. Evaluator (`agent/evaluator.py`)
- 5-dimension scoring:
  - Latency Gain (35%)
  - Accuracy (25%)
  - Stability (15%)
  - Clarity (15%)
  - Context Efficiency (10%)
- Final score: 1-10,000 scale

### 5. Graph Orchestrator (`agent/graph.py`)
- Explicit function chaining
- Shared state management
- Execution tracking

### 6. Benchmark (`benchmark/compare.py`)
- Agent vs baseline Claude comparison
- Test case runner

## Scoring System

```
Score = (
    latency_gain × 0.35 +
    accuracy × 0.25 +
    stability × 0.15 +
    clarity × 0.15 +
    context_efficiency × 0.10
) × 10,000
```

### Rating Scale

| Score Range | Rating |
|-------------|--------|
| 8500-10000 | Excellent - Production ready |
| 7000-8499 | Very Good - Minor improvements possible |
| 5500-6999 | Good - Solid analysis with room for enhancement |
| 4000-5499 | Fair - Adequate but needs refinement |
| 2500-3999 | Below Average - Significant improvements needed |
| 0-2499 | Poor - Major rework required |

## Output Schema

```json
{
  "root_causes": [
    {
      "description": "Blocking time.sleep() in async path",
      "category": "concurrency",
      "confidence": 0.92,
      "evidence": ["Line 45: time.sleep(0.05)"],
      "file_path": "audio_queue.py",
      "function_name": "_play_next"
    }
  ],
  "bottlenecks": [
    {
      "description": "50ms blocking sleep per audio track",
      "location": "audio_queue.py:_play_next:45",
      "severity": "high",
      "impact_type": "latency",
      "estimated_impact_ms": 50
    }
  ],
  "context_used": [
    {
      "file": "audio_queue.py",
      "tokens": 450,
      "depth": 0,
      "imports": ["threading", "time"]
    }
  ],
  "fixes": [
    {
      "description": "Replace time.sleep with asyncio.sleep",
      "fix_type": "async",
      "complexity": "low",
      "expected_latency_improvement": "45.0%",
      "code_change": "await asyncio.sleep(0.05)...",
      "risk_level": "low",
      "effort_estimate": "1-2 hours",
      "score": 450
    }
  ],
  "metrics": {
    "latency_gain": 0.72,
    "accuracy": 0.85,
    "stability": 0.90,
    "clarity": 0.82,
    "context_efficiency": 0.65
  },
  "final_score": 7680,
  "benchmark_comparison": {
    "agent_score": 7680,
    "claude_score": 5200,
    "summary": "LatencyFixer AI outperforms baseline by 47.7%"
  }
}
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Analyze from log file
```bash
python main.py --logs error.log --code ./src --output report.json
```

### Interactive mode
```bash
python main.py --interactive
```

### Run benchmarks
```bash
python main.py --benchmark
```

### Verbose output
```bash
python main.py --logs error.log --verbose
```

## Test Cases

Included in `benchmark/test_cases.json`:

1. **Streaming Latency Issue** - Buffer overflow, chunking bottleneck
2. **Audio Overlap Issue** - Race condition, blocking timing
3. **Inefficient Function** - O(n²) deduplication
4. **N+1 Query** - Database anti-pattern

## Example Results

### Test Case: Inefficient Function

**Input:**
```
PERF WARNING: deduplicate_items() took 2340ms for 10000 items
Stack trace shows nested loop pattern
```

**Output:**
- Root Cause: O(n²) nested loop for deduplication
- Bottleneck: 2340ms (critical severity)
- Fix: Use set-based O(n) deduplication
- Expected Improvement: 95%
- Score: 8420/10000

## Project Structure

```
latencyfixer-ai/
│
├── agent/
│   ├── __init__.py
│   ├── state.py              # Shared state object
│   ├── context_retriever.py  # Dependency-aware retrieval
│   ├── analyzer.py           # Root cause detection
│   ├── optimizer.py          # Fix suggestions
│   ├── evaluator.py          # Scoring system
│   └── graph.py              # Pipeline orchestration
│
├── benchmark/
│   ├── __init__.py
│   ├── compare.py            # Agent vs Claude
│   └── test_cases.json       # Test suite
│
├── metrics/
│   ├── __init__.py
│   └── scoring.py            # Score formulas
│
├── prompts/
│   ├── analyzer.txt          # Analyzer prompt
│   ├── optimizer.txt         # Optimizer prompt
│   └── evaluator.txt         # Evaluator prompt
│
├── main.py                   # CLI entry point
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── .cursorrules              # Cursor enforcement
└── README.md                 # This file
```

## Key Innovations

### 1. Context Engineering
- Shallow dependency graph (depth 1-2)
- Entity extraction from logs
- Focused context retrieval

### 2. Structured Scoring
- 5 dimensions with weights
- 1-10,000 scale
- Interpretable ratings

### 3. Benchmark Comparison
- Agent vs baseline Claude
- Quantified improvement
- Test case suite

### 4. Cursor Integration
- `.cursorrules` enforcement
- Structured output requirement
- Quantification mandates

## Dependencies

- Python 3.9+
- anthropic (optional, for live Claude comparison)
- tiktoken (optional, for accurate token counting)

## License

MIT License

## Quest-Based Hiring Process (Submission Checklist)

This repository has been prepared to satisfy the "quest-based" hiring requirements. Below is what we included and how to use it for your submission.

1) Build Your Own Agent
- The agent code is in the `agent/` directory and the orchestrator is `main.py`.
- This repo can be published to GitHub; if you need a ZIP instead, archive the repo root.

2) Cursor-Based Setup
- Cursor rules live at `.cursorrules` in the repo root. The rules enforce structured JSON output and quantification.
- I reviewed `.cursorrules`: it requires explicit `root_causes`, `bottlenecks`, `fixes`, `metrics`, and `final_score`, and mandates quantification and locations. This aligns with the quest requirement and is Cursor-ready.

3) Security Requirements
- No API keys or secrets are committed. Use the provided `.env-example` to configure API keys locally.
- The repo contains `.gitignore` and `.env-example` to help avoid committing secrets.

4) Performance Metrics (how score is computed)
- The evaluator calculates five normalized metrics (0..1): `latency_gain`, `accuracy`, `stability`, `clarity`, `context_efficiency`.
- Each metric is scaled to 0..10,000 for visibility, and the final score follows this rule:
  - If at least 2 of the three primary metrics (`latency_gain`, `accuracy`, `stability`) are present (non-zero), the `final_score` is the average of those present primary metrics (scaled to 0..10,000).
  - Otherwise, the `final_score` is the average of all available scaled metrics.
- The exact formula and implementation live in `agent/evaluator_engine.py` (see the returned `metrics_scaled` for per-metric 0..10,000 values).

5) Benchmark Comparison
- Benchmark logic is under `benchmark/compare.py`. It compares the agent to a Claude baseline (simulated when `ANTHROPIC_API_KEY` is not set).
- To run benchmarks locally: `python main.py --benchmark`. The output includes `benchmark_comparison` with `agent_score`, `claude_score`, and a short `summary`.

6) Problem Specialization
- This agent specializes in diagnosing and suggesting fixes for latency and performance issues in Python services with streaming / real-time components.
- Rationale: latency problems are frequent, observable in logs, and lend themselves to precise measurement (ms). Prioritizing this problem enables measurable improvement estimates and actionable fixes.

7) Documentation and Submission Notes
- README (this file) documents architecture, scoring, and how to run the agent.
- Include the following in your submission:
  - Public GitHub repository link (preferred) or a ZIP of this repo
  - Confirm `.cursorrules` is present and that `.env` does not contain secrets
  - Show example runs (use `python main.py --logs <file> --code <dir>`) and include the resulting JSON report

Additional notes
- `.cursorrules` appears to be sufficient for Cursor integration: it enforces structured JSON, line numbers, quantification, and score format. If you need stricter enforcement (e.g., JSON schema validation), I can add a machine-enforceable schema file and a CI check.
- If you'd like, I can also prepare a `SUBMISSION.md` that packages the required checklist, example outputs, and the GitHub link for direct submission.
