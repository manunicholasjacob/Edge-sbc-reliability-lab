"""
Reliability summary and scoring.

Generates comprehensive reliability reports combining all metrics.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run
from edge_sbc_reliability_lab.core.statistics import compute_stability_score


def compute_reliability_report(
    run_dir: Union[str, Path],
) -> Dict[str, Any]:
    """
    Generate a comprehensive reliability report for a benchmark run.
    
    Args:
        run_dir: Path to run directory
        
    Returns:
        Dictionary with reliability report
    """
    summary = summarize_run(run_dir)
    
    report = {
        "run_id": summary.get("run_id", ""),
        "model": summary.get("config", {}).get("model_name", ""),
        "runtime": summary.get("config", {}).get("runtime", ""),
    }
    
    # Latency reliability
    latency_stats = summary.get("latency_stats") or summary.get("results", {}).get("latency", {})
    if latency_stats:
        # Compute tail latency ratio
        p50 = latency_stats.get("p50_ms", 0)
        p99 = latency_stats.get("p99_ms", 0)
        tail_ratio = p99 / p50 if p50 > 0 else 0
        
        report["latency_reliability"] = {
            "mean_ms": latency_stats.get("mean_ms", 0),
            "p50_ms": p50,
            "p99_ms": p99,
            "tail_ratio": tail_ratio,
            "cv": latency_stats.get("cv", 0),
            "assessment": _assess_latency_reliability(tail_ratio, latency_stats.get("cv", 0)),
        }
    
    # Thermal reliability
    thermal = summary.get("thermal_summary", {})
    if thermal:
        temp_rise = thermal.get("rise_c", 0)
        peak_temp = thermal.get("max_c", 0)
        
        report["thermal_reliability"] = {
            "start_temp_c": thermal.get("start_c", 0),
            "peak_temp_c": peak_temp,
            "temp_rise_c": temp_rise,
            "assessment": _assess_thermal_reliability(peak_temp, temp_rise),
        }
    
    # Drift reliability
    drift = summary.get("drift_metrics", {})
    if drift:
        drift_pct = abs(drift.get("drift_pct", 0))
        
        report["drift_reliability"] = {
            "drift_percent": drift_pct,
            "early_mean_ms": drift.get("early_mean_ms", 0),
            "late_mean_ms": drift.get("late_mean_ms", 0),
            "assessment": _assess_drift_reliability(drift_pct),
        }
    
    # Overall reliability score
    report["overall_score"] = generate_reliability_score(report)
    report["overall_assessment"] = _get_overall_assessment(report["overall_score"])
    
    # Warnings
    warnings = summary.get("warnings", {}).get("warnings", [])
    report["warnings"] = warnings
    report["warning_count"] = len(warnings)
    
    return report


def generate_reliability_score(report: Dict[str, Any]) -> float:
    """
    Generate an overall reliability score from 0-100.
    
    Args:
        report: Reliability report dictionary
        
    Returns:
        Reliability score (0-100)
    """
    score = 100.0
    
    # Latency component (40 points max)
    latency = report.get("latency_reliability", {})
    if latency:
        tail_ratio = latency.get("tail_ratio", 1)
        cv = latency.get("cv", 0)
        
        # Penalize high tail ratio (p99/p50)
        if tail_ratio > 1.5:
            score -= min(20, (tail_ratio - 1.5) * 10)
        
        # Penalize high coefficient of variation
        score -= min(20, cv * 100)
    
    # Thermal component (30 points max)
    thermal = report.get("thermal_reliability", {})
    if thermal:
        peak_temp = thermal.get("peak_temp_c", 0)
        temp_rise = thermal.get("temp_rise_c", 0)
        
        # Penalize high peak temperature
        if peak_temp > 70:
            score -= min(15, (peak_temp - 70) * 1.5)
        
        # Penalize large temperature rise
        if temp_rise > 10:
            score -= min(15, (temp_rise - 10) * 1.5)
    
    # Drift component (20 points max)
    drift = report.get("drift_reliability", {})
    if drift:
        drift_pct = drift.get("drift_percent", 0)
        
        # Penalize drift
        score -= min(20, drift_pct * 2)
    
    # Warning penalty (10 points max)
    warning_count = report.get("warning_count", 0)
    score -= min(10, warning_count * 2)
    
    return max(0, min(100, score))


def _assess_latency_reliability(tail_ratio: float, cv: float) -> str:
    """Assess latency reliability."""
    if tail_ratio < 1.2 and cv < 0.05:
        return "excellent"
    elif tail_ratio < 1.5 and cv < 0.1:
        return "good"
    elif tail_ratio < 2.0 and cv < 0.2:
        return "acceptable"
    else:
        return "poor"


def _assess_thermal_reliability(peak_temp: float, temp_rise: float) -> str:
    """Assess thermal reliability."""
    if peak_temp < 60 and temp_rise < 10:
        return "excellent"
    elif peak_temp < 70 and temp_rise < 15:
        return "good"
    elif peak_temp < 80 and temp_rise < 20:
        return "acceptable"
    else:
        return "poor"


def _assess_drift_reliability(drift_pct: float) -> str:
    """Assess drift reliability."""
    if drift_pct < 2:
        return "excellent"
    elif drift_pct < 5:
        return "good"
    elif drift_pct < 10:
        return "acceptable"
    else:
        return "poor"


def _get_overall_assessment(score: float) -> str:
    """Get overall assessment from score."""
    if score >= 90:
        return "excellent - highly reliable for production deployment"
    elif score >= 75:
        return "good - suitable for most production use cases"
    elif score >= 50:
        return "acceptable - may need optimization for demanding applications"
    else:
        return "poor - significant reliability concerns, investigation recommended"


def generate_reliability_table(
    run_dirs: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate a reliability comparison table.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Optional path to save output
        
    Returns:
        Markdown table string
    """
    rows = []
    
    for run_dir in run_dirs:
        report = compute_reliability_report(run_dir)
        
        row = {
            "Run": report.get("run_id", "")[:30],
            "Runtime": report.get("runtime", ""),
            "Score": f"{report.get('overall_score', 0):.0f}",
            "Latency": report.get("latency_reliability", {}).get("assessment", "N/A"),
            "Thermal": report.get("thermal_reliability", {}).get("assessment", "N/A"),
            "Drift": report.get("drift_reliability", {}).get("assessment", "N/A"),
            "Warnings": report.get("warning_count", 0),
        }
        rows.append(row)
    
    # Generate markdown table
    if not rows:
        return "No runs to compare."
    
    headers = list(rows[0].keys())
    lines = []
    
    # Header
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Rows
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    
    result = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(result)
    
    return result
