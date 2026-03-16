"""
Leaderboard builder for benchmark results.

Aggregates benchmark results into a leaderboard-style summary table.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run


def build_leaderboard(
    run_dirs: List[Union[str, Path]],
    sort_by: str = "throughput",
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Build a leaderboard from multiple benchmark runs.
    
    Args:
        run_dirs: List of run directory paths
        sort_by: Column to sort by
        ascending: Sort order
        
    Returns:
        DataFrame with leaderboard
    """
    rows = []
    
    for run_dir in run_dirs:
        try:
            summary = summarize_run(run_dir)
            config = summary.get("config", {})
            stats = summary.get("latency_stats") or summary.get("results", {}).get("latency", {})
            thermal = summary.get("thermal_summary", {})
            drift = summary.get("drift_metrics", {})
            
            row = {
                "Model": config.get("model_name", "unknown"),
                "Runtime": config.get("runtime", "unknown"),
                "Batch": config.get("batch_size", 1),
                "Threads": config.get("threads", 4),
                "Mean (ms)": round(stats.get("mean_ms", 0), 2),
                "P50 (ms)": round(stats.get("p50_ms", 0), 2),
                "P90 (ms)": round(stats.get("p90_ms", 0), 2),
                "P99 (ms)": round(stats.get("p99_ms", 0), 2),
                "Throughput": round(stats.get("throughput_infs_per_sec", 0), 1),
                "Drift %": round(abs(drift.get("drift_pct", 0)), 1),
                "Temp Rise": round(thermal.get("rise_c", 0), 1),
                "Stability": round(summary.get("results", {}).get("stability_score", 0), 0),
                "Run ID": summary.get("run_id", "")[:25],
            }
            rows.append(row)
        except Exception as e:
            continue
    
    df = pd.DataFrame(rows)
    
    # Sort
    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending)
    
    # Add rank
    df.insert(0, "Rank", range(1, len(df) + 1))
    
    return df


def export_leaderboard(
    run_dirs: List[Union[str, Path]],
    output_path: Union[str, Path],
    format: str = "markdown",
    sort_by: str = "throughput",
) -> str:
    """
    Export leaderboard to file.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Output file path
        format: Output format ("markdown", "csv", "html")
        sort_by: Column to sort by
        
    Returns:
        Leaderboard string
    """
    df = build_leaderboard(run_dirs, sort_by=sort_by)
    
    if format == "csv":
        result = df.to_csv(index=False)
    elif format == "html":
        result = df.to_html(index=False, classes="leaderboard-table")
    else:
        result = df.to_markdown(index=False)
    
    with open(output_path, "w") as f:
        f.write(result)
    
    return result


def generate_leaderboard_report(
    run_dirs: List[Union[str, Path]],
    title: str = "Raspberry Pi 5 Inference Leaderboard",
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate a complete leaderboard report.
    
    Args:
        run_dirs: List of run directory paths
        title: Report title
        output_path: Optional output path
        
    Returns:
        Markdown report string
    """
    df = build_leaderboard(run_dirs)
    
    lines = [
        f"# {title}",
        "",
        f"**Total Runs**: {len(df)}",
        f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Performance Rankings",
        "",
        "### By Throughput (Higher is Better)",
        "",
    ]
    
    # Throughput leaderboard
    throughput_df = df.sort_values("Throughput", ascending=False).head(10)
    lines.append(throughput_df[["Rank", "Model", "Runtime", "Throughput", "Mean (ms)", "P99 (ms)"]].to_markdown(index=False))
    lines.append("")
    
    # Latency leaderboard
    lines.extend([
        "### By Mean Latency (Lower is Better)",
        "",
    ])
    latency_df = df.sort_values("Mean (ms)", ascending=True).head(10)
    lines.append(latency_df[["Rank", "Model", "Runtime", "Mean (ms)", "P99 (ms)", "Throughput"]].to_markdown(index=False))
    lines.append("")
    
    # Stability leaderboard
    lines.extend([
        "### By Stability Score (Higher is Better)",
        "",
    ])
    stability_df = df.sort_values("Stability", ascending=False).head(10)
    lines.append(stability_df[["Rank", "Model", "Runtime", "Stability", "Drift %", "Temp Rise"]].to_markdown(index=False))
    lines.append("")
    
    # Runtime comparison
    lines.extend([
        "## Runtime Comparison",
        "",
    ])
    
    runtime_summary = df.groupby("Runtime").agg({
        "Mean (ms)": "mean",
        "Throughput": "mean",
        "Stability": "mean",
    }).round(2)
    
    lines.append(runtime_summary.to_markdown())
    lines.append("")
    
    # Full table
    lines.extend([
        "## Complete Results",
        "",
        df.to_markdown(index=False),
    ])
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
    
    return report
