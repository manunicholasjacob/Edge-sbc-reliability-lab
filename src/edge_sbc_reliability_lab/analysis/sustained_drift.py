"""
Sustained drift analysis for long-running benchmarks.

Analyzes performance changes over time during sustained workloads.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd


def analyze_sustained_drift(
    latency_path: Union[str, Path],
    window_size: int = 100,
    n_segments: int = 10,
) -> Dict[str, Any]:
    """
    Analyze latency drift over a sustained benchmark run.
    
    Args:
        latency_path: Path to latency samples CSV
        window_size: Window size for moving average
        n_segments: Number of time segments for analysis
        
    Returns:
        Dictionary with drift analysis
    """
    df = pd.read_csv(latency_path)
    
    # Ensure latency column exists
    if "latency_ms" not in df.columns:
        if "latency_ns" in df.columns:
            df["latency_ms"] = df["latency_ns"] / 1e6
        else:
            return {"error": "No latency column found"}
    
    latencies = df["latency_ms"].values
    timestamps = df["timestamp_sec"].values if "timestamp_sec" in df.columns else np.arange(len(df)) / 100
    
    n = len(latencies)
    if n < window_size * 2:
        return {"error": f"Not enough samples ({n}) for drift analysis"}
    
    # Overall statistics
    overall_mean = float(np.mean(latencies))
    overall_std = float(np.std(latencies))
    
    # Early vs late comparison
    early_window = latencies[:window_size]
    late_window = latencies[-window_size:]
    
    early_mean = float(np.mean(early_window))
    late_mean = float(np.mean(late_window))
    
    drift_absolute = late_mean - early_mean
    drift_percent = (drift_absolute / early_mean * 100) if early_mean > 0 else 0
    
    # Moving average
    moving_avg = np.convolve(latencies, np.ones(window_size) / window_size, mode='valid')
    
    # Segment analysis
    segment_size = n // n_segments
    segments = []
    
    for i in range(n_segments):
        start_idx = i * segment_size
        end_idx = start_idx + segment_size if i < n_segments - 1 else n
        
        segment_latencies = latencies[start_idx:end_idx]
        segment_times = timestamps[start_idx:end_idx]
        
        segments.append({
            "segment": i + 1,
            "start_sec": float(segment_times[0]),
            "end_sec": float(segment_times[-1]),
            "mean_ms": float(np.mean(segment_latencies)),
            "std_ms": float(np.std(segment_latencies)),
            "p50_ms": float(np.percentile(segment_latencies, 50)),
            "p99_ms": float(np.percentile(segment_latencies, 99)),
            "min_ms": float(np.min(segment_latencies)),
            "max_ms": float(np.max(segment_latencies)),
            "count": len(segment_latencies),
        })
    
    # Trend analysis (linear regression)
    A = np.vstack([timestamps, np.ones(len(timestamps))]).T
    slope, intercept = np.linalg.lstsq(A, latencies, rcond=None)[0]
    
    # Stability metrics
    segment_means = [s["mean_ms"] for s in segments]
    stability_cv = float(np.std(segment_means) / np.mean(segment_means)) if np.mean(segment_means) > 0 else 0
    
    # Detect significant drift points
    drift_points = []
    threshold = overall_std * 2
    
    for i in range(1, len(segments)):
        diff = segments[i]["mean_ms"] - segments[i-1]["mean_ms"]
        if abs(diff) > threshold:
            drift_points.append({
                "segment": i + 1,
                "time_sec": segments[i]["start_sec"],
                "change_ms": float(diff),
                "change_pct": float(diff / segments[i-1]["mean_ms"] * 100),
            })
    
    return {
        "total_samples": n,
        "duration_sec": float(timestamps[-1] - timestamps[0]),
        "overall_mean_ms": overall_mean,
        "overall_std_ms": overall_std,
        "early_mean_ms": early_mean,
        "late_mean_ms": late_mean,
        "drift_absolute_ms": drift_absolute,
        "drift_percent": drift_percent,
        "trend_slope_ms_per_sec": float(slope),
        "stability_cv": stability_cv,
        "segments": segments,
        "drift_points": drift_points,
        "drift_classification": _classify_drift(drift_percent, stability_cv),
    }


def _classify_drift(drift_pct: float, stability_cv: float) -> str:
    """Classify drift severity."""
    drift_abs = abs(drift_pct)
    
    if drift_abs < 2 and stability_cv < 0.05:
        return "stable"
    elif drift_abs < 5 and stability_cv < 0.1:
        return "minor_drift"
    elif drift_abs < 10 and stability_cv < 0.15:
        return "moderate_drift"
    else:
        return "significant_drift"


def plot_drift_over_time(
    latency_path: Union[str, Path],
    output_path: Union[str, Path],
    thermal_path: Optional[Union[str, Path]] = None,
    title: str = "Latency Drift Over Time",
    window_size: int = 100,
) -> bool:
    """
    Generate drift visualization plot.
    
    Args:
        latency_path: Path to latency samples CSV
        output_path: Path to save plot
        thermal_path: Optional path to thermal trace for overlay
        title: Plot title
        window_size: Window size for moving average
        
    Returns:
        True if plot was generated successfully
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        df = pd.read_csv(latency_path)
        
        if "latency_ms" not in df.columns:
            df["latency_ms"] = df["latency_ns"] / 1e6
        
        timestamps = df["timestamp_sec"].values if "timestamp_sec" in df.columns else np.arange(len(df))
        latencies = df["latency_ms"].values
        
        # Compute moving average
        if len(latencies) > window_size:
            moving_avg = np.convolve(latencies, np.ones(window_size) / window_size, mode='valid')
            ma_timestamps = timestamps[window_size//2:window_size//2 + len(moving_avg)]
        else:
            moving_avg = latencies
            ma_timestamps = timestamps
        
        # Create figure
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Plot raw latencies (light)
        ax1.scatter(timestamps, latencies, alpha=0.1, s=1, c='blue', label='Raw latency')
        
        # Plot moving average
        ax1.plot(ma_timestamps, moving_avg, 'b-', linewidth=2, label=f'Moving avg ({window_size})')
        
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Latency (ms)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        
        # Add temperature overlay if available
        if thermal_path and Path(thermal_path).exists():
            thermal_df = pd.read_csv(thermal_path)
            if "temp_c" in thermal_df.columns:
                ax2 = ax1.twinx()
                thermal_times = thermal_df["timestamp_sec"].values if "timestamp_sec" in thermal_df.columns else np.arange(len(thermal_df))
                ax2.plot(thermal_times, thermal_df["temp_c"].values, 'r-', linewidth=1.5, alpha=0.7, label='Temperature')
                ax2.set_ylabel('Temperature (°C)', color='red')
                ax2.tick_params(axis='y', labelcolor='red')
        
        ax1.set_title(title)
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"Failed to generate plot: {e}")
        return False


def compute_stability_metrics(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute stability metrics from drift analysis.
    
    Args:
        analysis: Output from analyze_sustained_drift
        
    Returns:
        Dictionary with stability metrics
    """
    drift_pct = abs(analysis.get("drift_percent", 0))
    stability_cv = analysis.get("stability_cv", 0)
    trend_slope = abs(analysis.get("trend_slope_ms_per_sec", 0))
    
    # Stability score (0-100, higher is better)
    # Penalize drift, variability, and trend
    score = 100
    score -= min(30, drift_pct * 3)  # Up to 30 points for drift
    score -= min(30, stability_cv * 300)  # Up to 30 points for variability
    score -= min(20, trend_slope * 1000)  # Up to 20 points for trend
    score -= min(20, len(analysis.get("drift_points", [])) * 5)  # Up to 20 points for drift events
    
    score = max(0, min(100, score))
    
    # Classification
    if score >= 90:
        classification = "excellent"
    elif score >= 75:
        classification = "good"
    elif score >= 50:
        classification = "acceptable"
    else:
        classification = "poor"
    
    return {
        "stability_score": score,
        "classification": classification,
        "drift_percent": drift_pct,
        "variability_cv": stability_cv,
        "trend_slope_ms_per_sec": trend_slope,
        "drift_events": len(analysis.get("drift_points", [])),
        "recommendation": _get_stability_recommendation(classification, analysis),
    }


def _get_stability_recommendation(classification: str, analysis: Dict) -> str:
    """Get recommendation based on stability analysis."""
    if classification == "excellent":
        return "Performance is highly stable. Suitable for production deployment."
    elif classification == "good":
        return "Performance is stable with minor variations. Acceptable for most use cases."
    elif classification == "acceptable":
        drift = analysis.get("drift_classification", "")
        if "thermal" in str(analysis.get("drift_points", [])).lower():
            return "Performance shows some drift, possibly thermal-related. Consider improved cooling."
        else:
            return "Performance shows moderate drift. Monitor in production and consider longer warmup."
    else:
        return "Performance shows significant instability. Investigate thermal throttling, background processes, or hardware issues."
