"""
Thermal drift analysis for latency correlation.

Analyzes how inference latency changes with temperature over time.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def analyze_thermal_drift(
    latencies_ms: List[float],
    temperatures_c: List[float],
    timestamps_sec: List[float],
) -> Dict[str, float]:
    """
    Analyze thermal drift in latency measurements.
    
    Args:
        latencies_ms: Latency measurements in milliseconds
        temperatures_c: Temperature readings in Celsius
        timestamps_sec: Timestamps in seconds
        
    Returns:
        Dictionary with drift analysis metrics
    """
    if len(latencies_ms) < 10 or len(temperatures_c) < 2:
        return {
            "temp_rise_c": 0.0,
            "latency_drift_pct": 0.0,
            "correlation": 0.0,
            "time_to_thermal_stable_sec": 0.0,
            "stable_temp_c": 0.0,
        }
    
    latencies = np.array(latencies_ms)
    temps = np.array(temperatures_c)
    times = np.array(timestamps_sec)
    
    # Temperature rise
    temp_rise = temps[-1] - temps[0]
    
    # Latency drift (early vs late)
    n_window = min(10, len(latencies) // 4)
    early_latency = np.mean(latencies[:n_window])
    late_latency = np.mean(latencies[-n_window:])
    latency_drift_pct = ((late_latency - early_latency) / early_latency * 100) if early_latency > 0 else 0
    
    # Correlation between temperature and latency
    # Need to align timestamps - interpolate temps to latency timestamps
    if len(temps) > 1 and len(times) > 1:
        # Simple correlation using available data
        min_len = min(len(latencies), len(temps))
        correlation = float(np.corrcoef(latencies[:min_len], temps[:min_len])[0, 1])
        if np.isnan(correlation):
            correlation = 0.0
    else:
        correlation = 0.0
    
    # Time to thermal stability (when temp stops rising significantly)
    stable_time = 0.0
    stable_temp = temps[-1]
    
    if len(temps) > 5:
        # Look for when temperature change rate drops below threshold
        temp_diffs = np.diff(temps)
        time_diffs = np.diff(times[:len(temps)]) if len(times) >= len(temps) else np.ones(len(temp_diffs))
        
        # Avoid division by zero
        time_diffs = np.maximum(time_diffs, 0.1)
        temp_rates = temp_diffs / time_diffs  # °C per second
        
        # Find when rate drops below 0.1°C/sec for sustained period
        threshold = 0.1
        for i in range(len(temp_rates) - 2):
            if all(abs(r) < threshold for r in temp_rates[i:i+3]):
                stable_time = times[i] if i < len(times) else 0
                stable_temp = temps[i]
                break
    
    return {
        "temp_rise_c": float(temp_rise),
        "latency_drift_pct": float(latency_drift_pct),
        "correlation": float(correlation),
        "time_to_thermal_stable_sec": float(stable_time),
        "stable_temp_c": float(stable_temp),
        "start_temp_c": float(temps[0]),
        "end_temp_c": float(temps[-1]),
        "peak_temp_c": float(np.max(temps)),
    }


def compute_latency_temp_correlation(
    latency_df: pd.DataFrame,
    thermal_df: pd.DataFrame,
    latency_col: str = "latency_ms",
    temp_col: str = "temp_c",
    time_col: str = "timestamp_sec",
) -> Dict[str, float]:
    """
    Compute correlation between latency and temperature.
    
    Aligns timestamps and computes various correlation metrics.
    
    Args:
        latency_df: DataFrame with latency samples
        thermal_df: DataFrame with temperature samples
        latency_col: Column name for latency values
        temp_col: Column name for temperature values
        time_col: Column name for timestamps
        
    Returns:
        Dictionary with correlation metrics
    """
    if latency_df.empty or thermal_df.empty:
        return {
            "pearson_correlation": 0.0,
            "spearman_correlation": 0.0,
            "aligned_samples": 0,
        }
    
    # Interpolate temperature to latency timestamps
    latency_times = latency_df[time_col].values
    temp_times = thermal_df[time_col].values
    temp_values = thermal_df[temp_col].values
    
    # Interpolate temperatures at latency timestamps
    interpolated_temps = np.interp(latency_times, temp_times, temp_values)
    
    latencies = latency_df[latency_col].values
    
    # Pearson correlation
    if len(latencies) > 1 and np.std(latencies) > 0 and np.std(interpolated_temps) > 0:
        pearson = float(np.corrcoef(latencies, interpolated_temps)[0, 1])
        if np.isnan(pearson):
            pearson = 0.0
    else:
        pearson = 0.0
    
    # Spearman correlation (rank-based, more robust)
    try:
        from scipy import stats
        spearman, _ = stats.spearmanr(latencies, interpolated_temps)
        if np.isnan(spearman):
            spearman = 0.0
    except ImportError:
        # Fallback: use Pearson if scipy not available
        spearman = pearson
    
    return {
        "pearson_correlation": pearson,
        "spearman_correlation": float(spearman),
        "aligned_samples": len(latencies),
    }


def segment_by_temperature(
    latencies_ms: List[float],
    temperatures_c: List[float],
    n_segments: int = 5,
) -> List[Dict[str, float]]:
    """
    Segment latencies by temperature ranges.
    
    Args:
        latencies_ms: Latency measurements
        temperatures_c: Temperature readings (aligned with latencies)
        n_segments: Number of temperature segments
        
    Returns:
        List of dictionaries with segment statistics
    """
    if len(latencies_ms) < n_segments or len(temperatures_c) < n_segments:
        return []
    
    latencies = np.array(latencies_ms)
    temps = np.array(temperatures_c[:len(latencies)])
    
    # Create temperature bins
    temp_min, temp_max = np.min(temps), np.max(temps)
    if temp_max - temp_min < 1.0:
        # Not enough temperature variation
        return [{
            "temp_range_c": f"{temp_min:.1f}-{temp_max:.1f}",
            "mean_latency_ms": float(np.mean(latencies)),
            "std_latency_ms": float(np.std(latencies)),
            "sample_count": len(latencies),
        }]
    
    bin_edges = np.linspace(temp_min, temp_max, n_segments + 1)
    segments = []
    
    for i in range(n_segments):
        low, high = bin_edges[i], bin_edges[i + 1]
        mask = (temps >= low) & (temps < high if i < n_segments - 1 else temps <= high)
        segment_latencies = latencies[mask]
        
        if len(segment_latencies) > 0:
            segments.append({
                "temp_range_c": f"{low:.1f}-{high:.1f}",
                "temp_low_c": float(low),
                "temp_high_c": float(high),
                "mean_latency_ms": float(np.mean(segment_latencies)),
                "std_latency_ms": float(np.std(segment_latencies)),
                "p50_latency_ms": float(np.percentile(segment_latencies, 50)),
                "p99_latency_ms": float(np.percentile(segment_latencies, 99)),
                "sample_count": len(segment_latencies),
            })
    
    return segments


def compute_thermal_impact_score(drift_analysis: Dict[str, float]) -> float:
    """
    Compute a thermal impact score from 0-100.
    
    Higher scores indicate more thermal impact on performance.
    
    Args:
        drift_analysis: Output from analyze_thermal_drift
        
    Returns:
        Thermal impact score (0 = no impact, 100 = severe impact)
    """
    score = 0.0
    
    # Temperature rise contribution (0-30 points)
    # 0°C rise = 0 points, 20°C+ rise = 30 points
    temp_rise = abs(drift_analysis.get("temp_rise_c", 0))
    score += min(30, temp_rise * 1.5)
    
    # Latency drift contribution (0-40 points)
    # 0% drift = 0 points, 50%+ drift = 40 points
    latency_drift = abs(drift_analysis.get("latency_drift_pct", 0))
    score += min(40, latency_drift * 0.8)
    
    # Correlation contribution (0-30 points)
    # 0 correlation = 0 points, 1.0 correlation = 30 points
    correlation = abs(drift_analysis.get("correlation", 0))
    score += correlation * 30
    
    return min(100, max(0, score))
