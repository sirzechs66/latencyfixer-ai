#!/usr/bin/env python3
# Main entrypoint — small human note: CLI for running the LatencyFixer pipeline
# Supports interactive mode, file-based analysis, and benchmark runs.

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from agent.graph import run_latencyfixer
from benchmark.compare import BenchmarkRunner


console = Console()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LatencyFixer AI - LangGraph-based latency analysis agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze from log file and code directory
  python main.py --logs error.log --code ./src --output report.json

  # Run benchmark test cases
  python main.py --benchmark

  # Interactive mode (paste logs)
  python main.py --interactive

  # Analyze with custom base path
  python main.py --logs error.log --base-path ./project
        """
    )

    parser.add_argument(
        "--logs",
        type=str,
        help="Path to log file(s) containing error messages, stack traces"
    )
    parser.add_argument(
        "--code",
        type=str,
        help="Path to code directory for context retrieval"
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base path for code search (default: current directory)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="report.json",
        help="Output path for JSON report (default: report.json)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (paste logs manually)"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run benchmark test cases"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--no-benchmark",
        action="store_true",
        help="Disable benchmark comparison in report"
    )

    return parser.parse_args()


def load_logs(log_path: str) -> List[str]:
    """Load logs from file."""
    path = Path(log_path)
    if not path.exists():
        console.print(f"[red]Error: Log file not found: {log_path}[/red]")
        sys.exit(1)

    content = path.read_text()
    logs = [line.strip() for line in content.split("\n") if line.strip()]
    return logs


def load_code_snippets(code_path: str) -> Dict[str, str]:
    """Load code snippets from directory."""
    path = Path(code_path)
    if not path.exists():
        console.print(f"[yellow]Warning: Code path not found: {code_path}[/yellow]")
        return {}

    snippets = {}
    for py_file in path.rglob("*.py"):
        try:
            relative_path = py_file.relative_to(Path.cwd())
            snippets[str(relative_path)] = py_file.read_text()
        except Exception:
            continue

    return snippets


def run_interactive() -> tuple:
    """Run interactive mode - collect logs from user."""
    console.print(Panel.fit(
        "[bold blue]LatencyFixer AI - Interactive Mode[/bold blue]",
        subtitle="Paste your logs, stack traces, and error messages"
    ))
    console.print("\n[yellow]Paste your logs below. Press Ctrl+D (Unix) or Ctrl+Z then Enter (Windows) when done.[/yellow]\n")
    console.print("-" * 60)

    logs = []
    try:
        while True:
            line = input()
            if line.strip():
                logs.append(line)
    except EOFError:
        pass

    console.print("-" * 60)
    console.print(f"[green]Collected {len(logs)} log lines[/green]")

    # Optional: collect code snippet
    console.print("\n[yellow]Would you like to provide a code snippet? (y/n)[/yellow]")
    try:
        response = input().strip().lower()
        if response == "y":
            console.print("Paste the code content:")
            code_lines = []
            try:
                while True:
                    line = input()
                    code_lines.append(line)
            except EOFError:
                pass
            code_content = "\n".join(code_lines)
            return logs, {"pasted_code.py": code_content}
    except EOFError:
        pass

    return logs, {}


def run_benchmark() -> None:
    """Run benchmark test cases."""
    console.print(Panel.fit(
        "[bold blue]LatencyFixer AI - Benchmark Suite[/bold blue]",
        subtitle="Comparing agent vs baseline Claude"
    ))
    console.print()

    runner = BenchmarkRunner()
    results = runner.run_all_test_cases()

    console.print(f"[green]Ran {len(results)} test cases[/green]\n")

    # Create results table
    table = Table(title="Benchmark Results")
    table.add_column("Test Case", style="cyan")
    table.add_column("Agent Score", justify="right", style="green")
    table.add_column("Claude Score", justify="right", style="yellow")
    table.add_column("Improvement", justify="right", style="magenta")
    table.add_column("Summary", style="italic", max_width=50)

    for result in results:
        improvement = ""
        if result["claude_score"] > 0:
            pct = ((result["agent_score"] - result["claude_score"]) / result["claude_score"] * 100)
            improvement = f"{pct:+.1f}%"

        table.add_row(
            result["test_case"],
            f"{result['agent_score']:.0f}",
            f"{result['claude_score']:.0f}",
            improvement,
            result["summary"][:50] + "..." if len(result["summary"]) > 50 else result["summary"]
        )

    console.print(table)

    # Calculate aggregate
    avg_agent = sum(r["agent_score"] for r in results) / len(results)
    avg_claude = sum(r["claude_score"] for r in results) / len(results)

    console.print(Panel(
        f"[bold]Aggregate Results[/bold]\n\n"
        f"Average Agent Score: [green]{avg_agent:.0f}[/green]\n"
        f"Average Claude Score: [yellow]{avg_claude:.0f}[/yellow]\n"
        f"Improvement: [magenta]{((avg_agent - avg_claude) / avg_claude * 100) if avg_claude > 0 else 0:.1f}%[/magenta]"
    ))


def display_results(report: Dict, verbose: bool = False) -> None:
    """Display analysis results using Rich formatting."""
    # Final Score Panel
    score = report.get("final_score", 0)
    if score >= 8500:
        color = "green"
        rating = "Excellent - Production ready"
    elif score >= 7000:
        color = "bright_green"
        rating = "Very Good"
    elif score >= 5500:
        color = "yellow"
        rating = "Good"
    elif score >= 4000:
        color = "yellow"
        rating = "Fair"
    elif score >= 2500:
        color = "orange"
        rating = "Below Average"
    else:
        color = "red"
        rating = "Poor"

    console.print(Panel(
        f"[bold {color}]Score: {score:.0f} / 10,000[/bold {color}]\n"
        f"[{color}]{rating}[/{color}]",
        title="[bold]Evaluation Results[/bold]"
    ))

    # Metrics Table
    metrics = report.get("metrics", {})
    if metrics:
        table = Table(title="Dimension Scores")
        table.add_column("Dimension", style="cyan")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Weight", justify="right", style="yellow")

        weights = {
            "latency_gain": "35%",
            "accuracy": "25%",
            "stability": "15%",
            "clarity": "15%",
            "context_efficiency": "10%"
        }

        for dim, value in metrics.items():
            table.add_row(
                dim.replace("_", " ").title(),
                f"{value:.3f}",
                weights.get(dim, "-")
            )

        console.print(table)

    # Root Causes
    root_causes = report.get("root_causes", [])
    if root_causes:
        tree = Tree("[bold]Root Causes[/bold]")
        for i, rc in enumerate(root_causes, 1):
            branch = tree.add(f"[cyan]{rc.get('description', 'Unknown')}[/cyan]")
            branch.add(f"Category: [yellow]{rc.get('category', 'unknown')}[/yellow]")
            branch.add(f"Confidence: [green]{rc.get('confidence', 0):.0%}[/green]")
            if rc.get("file_path"):
                branch.add(f"File: [magenta]{rc.get('file_path')}[/magenta]")
        console.print(tree)

    # Bottlenecks
    bottlenecks = report.get("bottlenecks", [])
    if bottlenecks:
        table = Table(title="Detected Bottlenecks")
        table.add_column("Description", style="cyan", max_width=40)
        table.add_column("Severity", justify="center")
        table.add_column("Impact", justify="right")
        table.add_column("Est. Impact (ms)", justify="right")

        severity_colors = {
            "critical": "red",
            "high": "orange",
            "medium": "yellow",
            "low": "green"
        }

        for bn in bottlenecks:
            severity = bn.get("severity", "medium")
            color = severity_colors.get(severity, "white")
            table.add_row(
                bn.get("description", "Unknown")[:40],
                f"[{color}]{severity}[/{color}]",
                bn.get("impact_type", "unknown"),
                f"{bn.get('estimated_impact_ms', 0):.1f}"
            )

        console.print(table)

    # Fixes
    fixes = report.get("fixes", [])
    if fixes:
        table = Table(title="Optimization Recommendations")
        table.add_column("Fix", style="cyan", max_width=30)
        table.add_column("Type", justify="center")
        table.add_column("Complexity", justify="center")
        table.add_column("Improvement", justify="right", style="green")
        table.add_column("Effort", justify="right")

        for fix in fixes:
            table.add_row(
                fix.get("description", "Unknown")[:30],
                fix.get("fix_type", "unknown"),
                fix.get("complexity", "medium"),
                f"{fix.get('expected_latency_improvement_pct', 0):.1f}%",
                fix.get("effort_estimate", "unknown")
            )

        console.print(table)

    # Benchmark Comparison
    benchmark = report.get("benchmark_comparison", {})
    if benchmark and benchmark.get("summary") and benchmark.get("summary") != "Benchmark not configured":
        console.print(Panel(
            f"Agent Score: [green]{benchmark.get('agent_score', 0):.0f}[/green]\n"
            f"Claude Score: [yellow]{benchmark.get('claude_score', 0):.0f}[/yellow]\n\n"
            f"[italic]{benchmark.get('summary', '')}[/italic]",
            title="[bold]Benchmark Comparison[/bold]"
        ))


def run_analysis(
    logs: List[str],
    code_snippets: Dict[str, str],
    base_path: str,
    output_path: str,
    enable_benchmark: bool,
    verbose: bool
) -> Dict:
    """Run the full analysis pipeline."""
    console.print(Panel.fit(
        "[bold blue]LatencyFixer AI - Analysis Pipeline[/bold blue]",
        subtitle="LangGraph-based multi-stage agent system"
    ))
    console.print()

    console.print(f"[cyan]Input:[/cyan] {len(logs)} log entries, {len(code_snippets)} code files")

    # Run the LangGraph pipeline
    console.print("\n[bold]Executing pipeline...[/bold]")

    with console.status("[yellow]Running context retriever...[/yellow]"):
        pass

    try:
        report = run_latencyfixer(
            input_logs=logs,
            code_snippets=code_snippets,
            system_description="Performance latency analysis"
        )

        if enable_benchmark:
            with console.status("[yellow]Running benchmark comparison...[/yellow]"):
                runner = BenchmarkRunner()
                # Build a plain dict state for the benchmark runner (compare_with_claude expects a dict)
                state = {
                    "input_logs": logs,
                    "code_snippets": code_snippets,
                    "root_causes": report.get("root_causes", []),
                    "bottlenecks": report.get("bottlenecks", []),
                    "fixes": report.get("fixes", []),
                    "metrics": report.get("metrics", {}),
                    "final_score": report.get("final_score", 0),
                    "relevant_tokens": report.get("relevant_tokens", 1),
                    "context_tokens_total": report.get("context_tokens_total", 1),
                }
                benchmark_result = runner.compare_with_claude(state)
                report["benchmark_comparison"] = {
                    "agent_score": benchmark_result.agent_score,
                    "claude_score": benchmark_result.claude_score,
                    "summary": benchmark_result.summary
                }

        # Display results
        console.print()
        display_results(report, verbose)

        # Save report
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2))
        console.print(f"\n[green]Report saved to: {output_path}[/green]")

        return report

    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.interactive:
        logs, code_snippets = run_interactive()
        run_analysis(
            logs=logs,
            code_snippets=code_snippets,
            base_path=args.base_path,
            output_path=args.output,
            enable_benchmark=not args.no_benchmark,
            verbose=args.verbose
        )

    elif args.benchmark:
        run_benchmark()

    elif args.logs:
        logs = load_logs(args.logs)
        code_snippets = load_code_snippets(args.code) if args.code else {}

        run_analysis(
            logs=logs,
            code_snippets=code_snippets,
            base_path=args.base_path,
            output_path=args.output,
            enable_benchmark=not args.no_benchmark,
            verbose=args.verbose
        )

    else:
        console.print("[red]Error: Either --logs or --interactive is required[/red]")
        console.print("Use [cyan]--help[/cyan] for usage information")
        sys.exit(1)


if __name__ == "__main__":
    main()
