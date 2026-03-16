"""
Run comparison utilities.

Provides detailed side-by-side comparison of benchmark runs.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run
from edge_sbc_reliability_lab.analysis.fairness_checker import check_fairness


def compare_runs(
    run_dirs: List[Union[str, Path]],
    include_fairness: bool = True,
) -> Dict[str, Any]:
    """
    Compare multiple benchmark runs.
    
    Args:
        run_dirs: List of run directory paths
        include_fairness: Include fairness check
        
    Returns:
        Dictionary with comparison results
    """
    summaries = []
    for run_dir in run_dirs:
        summaries.append(summarize_run(run_dir))
    
    comparison = {
        "runs": [],
        "metrics_comparison": {},
        "config_comparison": {},
    }
    
    # Extract key metrics for each run
    for s in summaries:
        run_data = {
            "run_id": s.get("run_id", "unknown"),
            "runtime": s.get("config", {}).get("runtime", "unknown"),
            "model": s.get("config", {}).get("model_name", "unknown"),
        }
        
        # Latency metrics
        stats = s.get("latency_stats") or s.get("results", {}).get("latency", {})
        run_data["mean_ms"] = stats.get("mean_ms", 0)
        run_data["p50_ms"] = stats.get("p50_ms", 0)
        run_data["p90_ms"] = stats.get("p90_ms", 0)
        run_data["p99_ms"] = stats.get("p99_ms", 0)
        run_data["throughput"] = stats.get("throughput_infs_per_sec", 0)
        run_data["total_inferences"] = stats.get("count", 0)
        
        # Thermal metrics
        thermal = s.get("thermal_summary", {})
        run_data["temp_start_c"] = thermal.get("start_c", 0)
        run_data["temp_end_c"] = thermal.get("end_c", 0)
        run_data["temp_rise_c"] = thermal.get("rise_c", 0)
        
        # Drift metrics
        drift = s.get("drift_metrics", {})
        run_data["drift_pct"] = drift.get("drift_pct", 0)
        
        # Stability score
        run_data["stability_score"] = s.get("results", {}).get("stability_score", 0)
        
        comparison["runs"].append(run_data)
    
    # Compute deltas between runs
    if len(summaries) >= 2:
        baseline = comparison["runs"][0]
        
        for i, run in enumerate(comparison["runs"][1:], 1):
            deltas = {}
            
            for metric in ["mean_ms", "p50_ms", "p90_ms", "p99_ms"]:
                if baseline[metric] > 0:
                    delta_pct = ((run[metric] - baseline[metric]) / baseline[metric]) * 100
                    deltas[f"{metric}_delta_pct"] = delta_pct
            
            if baseline["throughput"] > 0:
                deltas["throughput_delta_pct"] = ((run["throughput"] - baseline["throughput"]) / baseline["throughput"]) * 100
            
            comparison["runs"][i]["deltas_vs_baseline"] = deltas
    
    # Fairness check
    if include_fairness:
        comparison["fairness"] = check_fairness(run_dirs)
    
    return comparison


def generate_comparison_markdown(
    run_dirs: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate markdown comparison report.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Optional path to save report
        
    Returns:
        Markdown report string
    """
    comparison = compare_runs(run_dirs)
    
    lines = [
        "# Benchmark Comparison Report",
        "",
        f"**Runs Compared**: {len(comparison['runs'])}",
        "",
    ]
    
    # Fairness warning
    fairness = comparison.get("fairness", {})
    if not fairness.get("comparable", True):
        lines.extend([
            "⚠️ **Warning**: Runs may not be directly comparable",
            "",
            fairness.get("message", ""),
            "",
        ])
    
    # Main comparison table
    lines.extend([
        "## Performance Comparison",
        "",
        "| Metric | " + " | ".join(r["run_id"][:20] for r in comparison["runs"]) + " |",
        "|--------|" + "|".join(["--------"] * len(comparison["runs"])) + "|",
    ])
    
    metrics = [
        ("Runtime", "runtime"),
        ("Mean Latency (ms)", "mean_ms"),
        ("P50 Latency (ms)", "p50_ms"),
        ("P90 Latency (ms)", "p90_ms"),
        ("P99 Latency (ms)", "p99_ms"),
        ("Throughput (inf/s)", "throughput"),
        ("Total Inferences", "total_inferences"),
        ("Temp Rise (°C)", "temp_rise_c"),
        ("Drift (%)", "drift_pct"),
        ("Stability Score", "stability_score"),
    ]
    
    for label, key in metrics:
        values = []
        for run in comparison["runs"]:
            val = run.get(key, "N/A")
            if isinstance(val, float):
                values.append(f"{val:.2f}")
            else:
                values.append(str(val))
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    
    lines.append("")
    
    # Delta analysis
    if len(comparison["runs"]) >= 2:
        lines.extend([
            "## Performance Delta (vs First Run)",
            "",
        ])
        
        for i, run in enumerate(comparison["runs"][1:], 1):
            deltas = run.get("deltas_vs_baseline", {})
            if deltas:
                lines.append(f"### {run['run_id']}")
                lines.append("")
                
                for key, value in deltas.items():
                    direction = "↑" if value > 0 else "↓" if value < 0 else "="
                    # For latency, lower is better
                    if "latency" in key.lower() or "_ms" in key:
                        quality = "worse" if value > 0 else "better"
                    else:
                        quality = "better" if value > 0 else "worse"
                    
                    metric_name = key.replace("_delta_pct", "").replace("_", " ").title()
                    lines.append(f"- **{metric_name}**: {direction} {abs(value):.1f}% ({quality})")
                
                lines.append("")
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
    
    return report


def find_best_run(
    run_dirs: List[Union[str, Path]],
    metric: str = "throughput",
    higher_is_better: bool = True,
) -> Dict[str, Any]:
    """
    Find the best performing run based on a metric.
    
    Args:
        run_dirs: List of run directory paths
        metric: Metric to compare
        higher_is_better: Whether higher values are better
        
    Returns:
        Dictionary with best run information
    """
    comparison = compare_runs(run_dirs, include_fairness=False)
    
    best_run = None
    best_value = None
    
    for run in comparison["runs"]:
        value = run.get(metric)
        if value is None:
            continue
        
        if best_value is None:
            best_value = value
            best_run = run
        elif higher_is_better and value > best_value:
            best_value = value
            best_run = run
        elif not higher_is_better and value < best_value:
            best_value = value
            best_run = run
    
    return {
        "best_run": best_run,
        "metric": metric,
        "value": best_value,
        "higher_is_better": higher_is_better,
    }
