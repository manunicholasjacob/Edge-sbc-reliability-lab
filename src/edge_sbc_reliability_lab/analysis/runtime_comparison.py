"""
Runtime comparison utilities.

Compares performance across different inference runtimes.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run


def compare_runtimes(
    run_dirs: List[Union[str, Path]],
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compare benchmark results across different runtimes.
    
    Args:
        run_dirs: List of run directory paths
        metrics: Metrics to compare (default: latency, throughput, thermal)
        
    Returns:
        Dictionary with comparison results
    """
    if metrics is None:
        metrics = ["mean_ms", "p50_ms", "p90_ms", "p99_ms", "throughput_infs_per_sec"]
    
    runs = []
    for run_dir in run_dirs:
        summary = summarize_run(run_dir)
        runs.append(summary)
    
    # Group by runtime
    by_runtime = {}
    for run in runs:
        runtime = run.get("config", {}).get("runtime", "unknown")
        if runtime not in by_runtime:
            by_runtime[runtime] = []
        by_runtime[runtime].append(run)
    
    # Compute comparison
    comparison = {
        "runtimes": list(by_runtime.keys()),
        "metrics": {},
    }
    
    for metric in metrics:
        comparison["metrics"][metric] = {}
        
        for runtime, runtime_runs in by_runtime.items():
            values = []
            for run in runtime_runs:
                # Try to get metric from latency_stats or results
                if "latency_stats" in run:
                    value = run["latency_stats"].get(metric)
                elif "results" in run and "latency" in run["results"]:
                    value = run["results"]["latency"].get(metric)
                else:
                    value = None
                
                if value is not None:
                    values.append(value)
            
            if values:
                comparison["metrics"][metric][runtime] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }
    
    # Find best runtime for each metric
    comparison["best"] = {}
    for metric in metrics:
        metric_data = comparison["metrics"].get(metric, {})
        if metric_data:
            # Lower is better for latency, higher for throughput
            is_lower_better = "latency" in metric.lower() or metric.endswith("_ms")
            
            if is_lower_better:
                best = min(metric_data.items(), key=lambda x: x[1]["mean"])
            else:
                best = max(metric_data.items(), key=lambda x: x[1]["mean"])
            
            comparison["best"][metric] = best[0]
    
    return comparison


def generate_comparison_table(
    run_dirs: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
    format: str = "markdown",
) -> str:
    """
    Generate a comparison table across runs.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Optional path to save output
        format: Output format ("markdown", "csv", "html")
        
    Returns:
        Formatted table string
    """
    rows = []
    
    for run_dir in run_dirs:
        summary = summarize_run(run_dir)
        config = summary.get("config", {})
        
        row = {
            "Runtime": config.get("runtime", "N/A"),
            "Model": config.get("model_name", "N/A"),
            "Batch": config.get("batch_size", 1),
            "Threads": config.get("threads", 4),
        }
        
        # Get latency stats
        stats = summary.get("latency_stats") or summary.get("results", {}).get("latency", {})
        row["Mean (ms)"] = f"{stats.get('mean_ms', 0):.2f}"
        row["P50 (ms)"] = f"{stats.get('p50_ms', 0):.2f}"
        row["P90 (ms)"] = f"{stats.get('p90_ms', 0):.2f}"
        row["P99 (ms)"] = f"{stats.get('p99_ms', 0):.2f}"
        row["Throughput"] = f"{stats.get('throughput_infs_per_sec', 0):.1f}"
        
        # Thermal
        thermal = summary.get("thermal_summary", {})
        row["Temp Rise (°C)"] = f"{thermal.get('rise_c', 0):.1f}"
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    if format == "csv":
        result = df.to_csv(index=False)
    elif format == "html":
        result = df.to_html(index=False)
    else:  # markdown
        result = df.to_markdown(index=False)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(result)
    
    return result


def compute_speedup(
    baseline_run: Union[str, Path],
    comparison_runs: List[Union[str, Path]],
) -> Dict[str, float]:
    """
    Compute speedup relative to a baseline run.
    
    Args:
        baseline_run: Path to baseline run directory
        comparison_runs: Paths to comparison run directories
        
    Returns:
        Dictionary mapping run_id to speedup factor
    """
    baseline = summarize_run(baseline_run)
    baseline_stats = baseline.get("latency_stats") or baseline.get("results", {}).get("latency", {})
    baseline_latency = baseline_stats.get("mean_ms", 0)
    
    if baseline_latency <= 0:
        return {}
    
    speedups = {}
    
    for run_dir in comparison_runs:
        summary = summarize_run(run_dir)
        stats = summary.get("latency_stats") or summary.get("results", {}).get("latency", {})
        latency = stats.get("mean_ms", 0)
        
        if latency > 0:
            speedup = baseline_latency / latency
            speedups[summary.get("run_id", str(run_dir))] = speedup
    
    return speedups
