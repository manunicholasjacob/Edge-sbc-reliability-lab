"""
Latency vs temperature analysis.

Analyzes the relationship between inference latency and CPU temperature.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


def analyze_latency_temperature(
    latency_path: Union[str, Path],
    thermal_path: Union[str, Path],
) -> Dict[str, Any]:
    """
    Analyze relationship between latency and temperature.
    
    Args:
        latency_path: Path to latency samples CSV
        thermal_path: Path to thermal trace CSV
        
    Returns:
        Dictionary with correlation analysis
    """
    latency_df = pd.read_csv(latency_path)
    thermal_df = pd.read_csv(thermal_path)
    
    # Ensure required columns exist
    if "latency_ms" not in latency_df.columns:
        if "latency_ns" in latency_df.columns:
            latency_df["latency_ms"] = latency_df["latency_ns"] / 1e6
        else:
            return {"error": "No latency column found"}
    
    if "temp_c" not in thermal_df.columns:
        return {"error": "No temperature column found"}
    
    # Get timestamps
    latency_times = latency_df["timestamp_sec"].values if "timestamp_sec" in latency_df.columns else np.arange(len(latency_df))
    thermal_times = thermal_df["timestamp_sec"].values if "timestamp_sec" in thermal_df.columns else np.arange(len(thermal_df))
    
    # Interpolate temperature to latency timestamps
    temps_at_latency = np.interp(latency_times, thermal_times, thermal_df["temp_c"].values)
    latencies = latency_df["latency_ms"].values
    
    # Compute correlation
    if len(latencies) > 1 and np.std(latencies) > 0 and np.std(temps_at_latency) > 0:
        correlation = float(np.corrcoef(latencies, temps_at_latency)[0, 1])
    else:
        correlation = 0.0
    
    # Segment analysis
    temp_min, temp_max = np.min(temps_at_latency), np.max(temps_at_latency)
    temp_range = temp_max - temp_min
    
    segments = []
    if temp_range > 2:  # At least 2°C range
        n_segments = min(5, int(temp_range / 2))
        bin_edges = np.linspace(temp_min, temp_max, n_segments + 1)
        
        for i in range(n_segments):
            low, high = bin_edges[i], bin_edges[i + 1]
            mask = (temps_at_latency >= low) & (temps_at_latency < high if i < n_segments - 1 else temps_at_latency <= high)
            segment_latencies = latencies[mask]
            
            if len(segment_latencies) > 0:
                segments.append({
                    "temp_range": f"{low:.1f}-{high:.1f}°C",
                    "temp_mid": (low + high) / 2,
                    "mean_latency_ms": float(np.mean(segment_latencies)),
                    "std_latency_ms": float(np.std(segment_latencies)),
                    "p99_latency_ms": float(np.percentile(segment_latencies, 99)),
                    "sample_count": len(segment_latencies),
                })
    
    # Linear regression
    if len(latencies) > 10:
        # Simple linear regression: latency = a * temp + b
        A = np.vstack([temps_at_latency, np.ones(len(temps_at_latency))]).T
        slope, intercept = np.linalg.lstsq(A, latencies, rcond=None)[0]
    else:
        slope, intercept = 0.0, 0.0
    
    return {
        "correlation": correlation,
        "temp_range_c": float(temp_range),
        "temp_min_c": float(temp_min),
        "temp_max_c": float(temp_max),
        "latency_mean_ms": float(np.mean(latencies)),
        "latency_std_ms": float(np.std(latencies)),
        "regression_slope": float(slope),  # ms per °C
        "regression_intercept": float(intercept),
        "segments": segments,
        "sample_count": len(latencies),
    }


def plot_latency_vs_temp(
    latency_path: Union[str, Path],
    thermal_path: Union[str, Path],
    output_path: Union[str, Path],
    title: str = "Latency vs Temperature",
) -> bool:
    """
    Generate latency vs temperature scatter plot.
    
    Args:
        latency_path: Path to latency samples CSV
        thermal_path: Path to thermal trace CSV
        output_path: Path to save plot
        title: Plot title
        
    Returns:
        True if plot was generated successfully
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        latency_df = pd.read_csv(latency_path)
        thermal_df = pd.read_csv(thermal_path)
        
        # Prepare data
        if "latency_ms" not in latency_df.columns:
            latency_df["latency_ms"] = latency_df["latency_ns"] / 1e6
        
        latency_times = latency_df["timestamp_sec"].values
        thermal_times = thermal_df["timestamp_sec"].values
        
        temps_at_latency = np.interp(latency_times, thermal_times, thermal_df["temp_c"].values)
        latencies = latency_df["latency_ms"].values
        
        # Create plot
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Scatter plot with alpha for density
        ax.scatter(temps_at_latency, latencies, alpha=0.3, s=10, c='blue')
        
        # Add trend line
        z = np.polyfit(temps_at_latency, latencies, 1)
        p = np.poly1d(z)
        temp_range = np.linspace(temps_at_latency.min(), temps_at_latency.max(), 100)
        ax.plot(temp_range, p(temp_range), 'r-', linewidth=2, label=f'Trend: {z[0]:.3f} ms/°C')
        
        ax.set_xlabel('Temperature (°C)')
        ax.set_ylabel('Latency (ms)')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"Failed to generate plot: {e}")
        return False


def compute_thermal_sensitivity(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute thermal sensitivity metrics from analysis.
    
    Args:
        analysis: Output from analyze_latency_temperature
        
    Returns:
        Dictionary with sensitivity metrics
    """
    slope = analysis.get("regression_slope", 0)
    correlation = analysis.get("correlation", 0)
    temp_range = analysis.get("temp_range_c", 0)
    
    # Sensitivity classification
    if abs(slope) < 0.01:
        sensitivity = "negligible"
    elif abs(slope) < 0.05:
        sensitivity = "low"
    elif abs(slope) < 0.1:
        sensitivity = "moderate"
    else:
        sensitivity = "high"
    
    # Estimated latency increase over temperature range
    latency_increase_ms = abs(slope) * temp_range
    latency_increase_pct = (latency_increase_ms / analysis.get("latency_mean_ms", 1)) * 100
    
    return {
        "sensitivity_class": sensitivity,
        "slope_ms_per_c": slope,
        "correlation": correlation,
        "temp_range_c": temp_range,
        "estimated_latency_increase_ms": latency_increase_ms,
        "estimated_latency_increase_pct": latency_increase_pct,
        "recommendation": _get_thermal_recommendation(sensitivity, correlation),
    }


def _get_thermal_recommendation(sensitivity: str, correlation: float) -> str:
    """Get recommendation based on thermal sensitivity."""
    if sensitivity == "negligible":
        return "Thermal impact is minimal. No special cooling measures needed for this workload."
    elif sensitivity == "low":
        return "Low thermal sensitivity. Standard passive cooling should be sufficient."
    elif sensitivity == "moderate":
        if correlation > 0.5:
            return "Moderate thermal sensitivity with clear correlation. Consider active cooling for sustained workloads."
        else:
            return "Moderate thermal sensitivity but weak correlation. Monitor temperature during extended runs."
    else:
        return "High thermal sensitivity. Active cooling strongly recommended for consistent performance."
