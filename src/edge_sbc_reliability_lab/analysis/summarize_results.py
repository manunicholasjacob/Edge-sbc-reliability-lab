"""
Result summarization utilities.

Generates comprehensive summaries from benchmark run data.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from edge_sbc_reliability_lab.core.output import OutputManager
from edge_sbc_reliability_lab.core.statistics import compute_latency_stats, compute_drift_metrics


def summarize_run(run_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Generate a comprehensive summary from a benchmark run directory.
    
    Args:
        run_dir: Path to run directory
        
    Returns:
        Dictionary with complete run summary
    """
    run_dir = Path(run_dir)
    
    summary = {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
    }
    
    # Load manifest
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        summary["manifest"] = OutputManager.load_json(manifest_path)
    
    # Load config
    config_path = run_dir / "config_resolved.yaml"
    if config_path.exists():
        summary["config"] = OutputManager.load_yaml(config_path)
    
    # Load existing summary
    summary_path = run_dir / "summary.json"
    if summary_path.exists():
        summary["results"] = OutputManager.load_json(summary_path)
    
    # Load system snapshot
    snapshot_path = run_dir / "system_snapshot.json"
    if snapshot_path.exists():
        summary["system"] = OutputManager.load_json(snapshot_path)
    
    # Load warnings
    warnings_path = run_dir / "warnings.json"
    if warnings_path.exists():
        summary["warnings"] = OutputManager.load_json(warnings_path)
    
    # Compute additional statistics from raw data if available
    latency_path = run_dir / "latency_samples.csv"
    if latency_path.exists():
        df = pd.read_csv(latency_path)
        if "latency_ns" in df.columns:
            latencies_ns = df["latency_ns"].tolist()
            timestamps_ns = df["timestamp_ns"].tolist() if "timestamp_ns" in df.columns else []
            
            stats = compute_latency_stats(latencies_ns)
            summary["latency_stats"] = stats.to_dict()
            
            if timestamps_ns:
                drift = compute_drift_metrics(latencies_ns, timestamps_ns)
                summary["drift_metrics"] = drift
    
    # Load thermal data
    thermal_path = run_dir / "thermal_trace.csv"
    if thermal_path.exists():
        df = pd.read_csv(thermal_path)
        if "temp_c" in df.columns:
            summary["thermal_summary"] = {
                "min_c": float(df["temp_c"].min()),
                "max_c": float(df["temp_c"].max()),
                "mean_c": float(df["temp_c"].mean()),
                "start_c": float(df["temp_c"].iloc[0]),
                "end_c": float(df["temp_c"].iloc[-1]),
                "rise_c": float(df["temp_c"].iloc[-1] - df["temp_c"].iloc[0]),
            }
    
    return summary


def summarize_multiple_runs(
    run_dirs: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Summarize multiple benchmark runs into a comparison table.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Optional path to save CSV output
        
    Returns:
        DataFrame with summary of all runs
    """
    rows = []
    
    for run_dir in run_dirs:
        try:
            summary = summarize_run(run_dir)
            
            row = {
                "run_id": summary.get("run_id", ""),
                "experiment": summary.get("config", {}).get("experiment_name", ""),
                "model": summary.get("config", {}).get("model_name", ""),
                "runtime": summary.get("config", {}).get("runtime", ""),
                "batch_size": summary.get("config", {}).get("batch_size", 1),
                "threads": summary.get("config", {}).get("threads", 4),
            }
            
            # Add latency stats
            if "latency_stats" in summary:
                stats = summary["latency_stats"]
                row.update({
                    "mean_ms": stats.get("mean_ms", 0),
                    "p50_ms": stats.get("p50_ms", 0),
                    "p90_ms": stats.get("p90_ms", 0),
                    "p99_ms": stats.get("p99_ms", 0),
                    "throughput": stats.get("throughput_infs_per_sec", 0),
                    "total_inferences": stats.get("count", 0),
                })
            elif "results" in summary and "latency" in summary["results"]:
                stats = summary["results"]["latency"]
                row.update({
                    "mean_ms": stats.get("mean_ms", 0),
                    "p50_ms": stats.get("p50_ms", 0),
                    "p90_ms": stats.get("p90_ms", 0),
                    "p99_ms": stats.get("p99_ms", 0),
                    "throughput": stats.get("throughput_infs_per_sec", 0),
                    "total_inferences": stats.get("count", 0),
                })
            
            # Add thermal summary
            if "thermal_summary" in summary:
                thermal = summary["thermal_summary"]
                row.update({
                    "temp_start_c": thermal.get("start_c", 0),
                    "temp_end_c": thermal.get("end_c", 0),
                    "temp_rise_c": thermal.get("rise_c", 0),
                    "temp_max_c": thermal.get("max_c", 0),
                })
            
            # Add drift metrics
            if "drift_metrics" in summary:
                drift = summary["drift_metrics"]
                row["drift_pct"] = drift.get("drift_pct", 0)
            
            # Add stability score
            if "results" in summary:
                row["stability_score"] = summary["results"].get("stability_score", 0)
            
            rows.append(row)
            
        except Exception as e:
            rows.append({
                "run_id": str(run_dir),
                "error": str(e),
            })
    
    df = pd.DataFrame(rows)
    
    if output_path:
        df.to_csv(output_path, index=False)
    
    return df


def generate_summary_report(
    run_dir: Union[str, Path],
    output_format: str = "markdown",
) -> str:
    """
    Generate a human-readable summary report.
    
    Args:
        run_dir: Path to run directory
        output_format: Output format ("markdown" or "text")
        
    Returns:
        Formatted report string
    """
    summary = summarize_run(run_dir)
    
    lines = []
    
    if output_format == "markdown":
        lines.append(f"# Benchmark Summary: {summary.get('run_id', 'Unknown')}")
        lines.append("")
        
        # Configuration
        config = summary.get("config", {})
        lines.append("## Configuration")
        lines.append(f"- **Model**: {config.get('model_name', 'N/A')}")
        lines.append(f"- **Runtime**: {config.get('runtime', 'N/A')}")
        lines.append(f"- **Batch Size**: {config.get('batch_size', 'N/A')}")
        lines.append(f"- **Threads**: {config.get('threads', 'N/A')}")
        lines.append("")
        
        # Latency Results
        if "latency_stats" in summary:
            stats = summary["latency_stats"]
            lines.append("## Latency Results")
            lines.append(f"- **Total Inferences**: {stats.get('count', 0):,}")
            lines.append(f"- **Mean Latency**: {stats.get('mean_ms', 0):.3f} ms")
            lines.append(f"- **P50 Latency**: {stats.get('p50_ms', 0):.3f} ms")
            lines.append(f"- **P90 Latency**: {stats.get('p90_ms', 0):.3f} ms")
            lines.append(f"- **P99 Latency**: {stats.get('p99_ms', 0):.3f} ms")
            lines.append(f"- **Throughput**: {stats.get('throughput_infs_per_sec', 0):.2f} inf/s")
            lines.append("")
        
        # Thermal Results
        if "thermal_summary" in summary:
            thermal = summary["thermal_summary"]
            lines.append("## Thermal Behavior")
            lines.append(f"- **Start Temperature**: {thermal.get('start_c', 0):.1f}°C")
            lines.append(f"- **End Temperature**: {thermal.get('end_c', 0):.1f}°C")
            lines.append(f"- **Temperature Rise**: {thermal.get('rise_c', 0):.1f}°C")
            lines.append(f"- **Peak Temperature**: {thermal.get('max_c', 0):.1f}°C")
            lines.append("")
        
        # Warnings
        warnings = summary.get("warnings", {}).get("warnings", [])
        if warnings:
            lines.append("## Warnings")
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")
    
    else:
        # Plain text format
        lines.append(f"Benchmark Summary: {summary.get('run_id', 'Unknown')}")
        lines.append("=" * 60)
        
        config = summary.get("config", {})
        lines.append(f"Model: {config.get('model_name', 'N/A')}")
        lines.append(f"Runtime: {config.get('runtime', 'N/A')}")
        
        if "latency_stats" in summary:
            stats = summary["latency_stats"]
            lines.append(f"Mean Latency: {stats.get('mean_ms', 0):.3f} ms")
            lines.append(f"Throughput: {stats.get('throughput_infs_per_sec', 0):.2f} inf/s")
    
    return "\n".join(lines)
