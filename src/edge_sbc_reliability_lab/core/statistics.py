"""
Statistical utilities for latency analysis.

Provides comprehensive latency statistics including percentiles,
stability metrics, and drift analysis.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class LatencyStats:
    """Comprehensive latency statistics."""
    
    count: int
    mean_ms: float
    median_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    p999_ms: float
    iqr_ms: float  # Interquartile range
    cv: float  # Coefficient of variation
    throughput_infs_per_sec: float
    total_time_sec: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "std_ms": self.std_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "p50_ms": self.p50_ms,
            "p90_ms": self.p90_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "p999_ms": self.p999_ms,
            "iqr_ms": self.iqr_ms,
            "cv": self.cv,
            "throughput_infs_per_sec": self.throughput_infs_per_sec,
            "total_time_sec": self.total_time_sec,
        }


def compute_latency_stats(latencies_ns: List[int], total_time_ns: Optional[int] = None) -> LatencyStats:
    """
    Compute comprehensive latency statistics.
    
    Args:
        latencies_ns: List of latency measurements in nanoseconds
        total_time_ns: Optional total wall-clock time in nanoseconds
        
    Returns:
        LatencyStats with all computed metrics
    """
    if not latencies_ns:
        return LatencyStats(
            count=0, mean_ms=0, median_ms=0, std_ms=0, min_ms=0, max_ms=0,
            p50_ms=0, p90_ms=0, p95_ms=0, p99_ms=0, p999_ms=0,
            iqr_ms=0, cv=0, throughput_infs_per_sec=0, total_time_sec=0
        )
    
    # Convert to numpy array in milliseconds
    latencies_ms = np.array(latencies_ns, dtype=np.float64) / 1e6
    
    count = len(latencies_ms)
    mean_ms = float(np.mean(latencies_ms))
    median_ms = float(np.median(latencies_ms))
    std_ms = float(np.std(latencies_ms))
    min_ms = float(np.min(latencies_ms))
    max_ms = float(np.max(latencies_ms))
    
    # Percentiles
    p50_ms = float(np.percentile(latencies_ms, 50))
    p90_ms = float(np.percentile(latencies_ms, 90))
    p95_ms = float(np.percentile(latencies_ms, 95))
    p99_ms = float(np.percentile(latencies_ms, 99))
    p999_ms = float(np.percentile(latencies_ms, 99.9))
    
    # Interquartile range
    q75 = float(np.percentile(latencies_ms, 75))
    q25 = float(np.percentile(latencies_ms, 25))
    iqr_ms = q75 - q25
    
    # Coefficient of variation (relative standard deviation)
    cv = std_ms / mean_ms if mean_ms > 0 else 0
    
    # Total time and throughput
    if total_time_ns is not None:
        total_time_sec = total_time_ns / 1e9
    else:
        total_time_sec = sum(latencies_ns) / 1e9
    
    throughput = count / total_time_sec if total_time_sec > 0 else 0
    
    return LatencyStats(
        count=count,
        mean_ms=mean_ms,
        median_ms=median_ms,
        std_ms=std_ms,
        min_ms=min_ms,
        max_ms=max_ms,
        p50_ms=p50_ms,
        p90_ms=p90_ms,
        p95_ms=p95_ms,
        p99_ms=p99_ms,
        p999_ms=p999_ms,
        iqr_ms=iqr_ms,
        cv=cv,
        throughput_infs_per_sec=throughput,
        total_time_sec=total_time_sec,
    )


def compute_drift_metrics(
    latencies_ns: List[int],
    timestamps_ns: List[int],
    window_size: int = 10
) -> Dict[str, float]:
    """
    Compute latency drift metrics over time.
    
    Args:
        latencies_ns: List of latency measurements in nanoseconds
        timestamps_ns: List of timestamps in nanoseconds
        window_size: Number of samples for moving average
        
    Returns:
        Dictionary with drift metrics
    """
    if len(latencies_ns) < window_size * 2:
        return {
            "drift_pct": 0.0,
            "early_mean_ms": 0.0,
            "late_mean_ms": 0.0,
            "max_deviation_pct": 0.0,
            "trend_slope_ms_per_sec": 0.0,
        }
    
    latencies_ms = np.array(latencies_ns, dtype=np.float64) / 1e6
    timestamps_sec = np.array(timestamps_ns, dtype=np.float64) / 1e9
    
    # Early vs late comparison
    early_mean = float(np.mean(latencies_ms[:window_size]))
    late_mean = float(np.mean(latencies_ms[-window_size:]))
    
    drift_pct = ((late_mean - early_mean) / early_mean * 100) if early_mean > 0 else 0
    
    # Maximum deviation from overall mean
    overall_mean = float(np.mean(latencies_ms))
    max_deviation = float(np.max(np.abs(latencies_ms - overall_mean)))
    max_deviation_pct = (max_deviation / overall_mean * 100) if overall_mean > 0 else 0
    
    # Linear trend (slope)
    if len(timestamps_sec) > 1:
        # Simple linear regression
        x = timestamps_sec - timestamps_sec[0]
        y = latencies_ms
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_xx = np.sum(x * x)
        
        denominator = n * sum_xx - sum_x * sum_x
        if abs(denominator) > 1e-10:
            slope = (n * sum_xy - sum_x * sum_y) / denominator
        else:
            slope = 0.0
    else:
        slope = 0.0
    
    return {
        "drift_pct": drift_pct,
        "early_mean_ms": early_mean,
        "late_mean_ms": late_mean,
        "max_deviation_pct": max_deviation_pct,
        "trend_slope_ms_per_sec": float(slope),
    }


def compute_stability_score(stats: LatencyStats, drift_metrics: Dict[str, float]) -> float:
    """
    Compute a stability score from 0-100.
    
    Higher scores indicate more stable performance.
    
    Args:
        stats: Latency statistics
        drift_metrics: Drift metrics from compute_drift_metrics
        
    Returns:
        Stability score from 0 to 100
    """
    if stats.count == 0:
        return 0.0
    
    # Components (each 0-25 points)
    
    # 1. Low coefficient of variation (25 points max)
    # CV of 0 = 25 points, CV of 0.5+ = 0 points
    cv_score = max(0, 25 * (1 - stats.cv * 2))
    
    # 2. Low p99/p50 ratio (25 points max)
    # Ratio of 1 = 25 points, ratio of 3+ = 0 points
    if stats.p50_ms > 0:
        p99_ratio = stats.p99_ms / stats.p50_ms
        ratio_score = max(0, 25 * (1 - (p99_ratio - 1) / 2))
    else:
        ratio_score = 0
    
    # 3. Low drift (25 points max)
    # 0% drift = 25 points, 20%+ drift = 0 points
    drift_pct = abs(drift_metrics.get("drift_pct", 0))
    drift_score = max(0, 25 * (1 - drift_pct / 20))
    
    # 4. Low max deviation (25 points max)
    # 0% deviation = 25 points, 50%+ deviation = 0 points
    max_dev_pct = drift_metrics.get("max_deviation_pct", 0)
    deviation_score = max(0, 25 * (1 - max_dev_pct / 50))
    
    total_score = cv_score + ratio_score + drift_score + deviation_score
    return min(100, max(0, total_score))


def detect_outliers(
    latencies_ns: List[int],
    method: str = "iqr",
    threshold: float = 1.5
) -> Tuple[List[int], List[int]]:
    """
    Detect outliers in latency measurements.
    
    Args:
        latencies_ns: List of latency measurements
        method: Detection method ("iqr" or "zscore")
        threshold: Threshold for outlier detection
        
    Returns:
        Tuple of (outlier_indices, outlier_values)
    """
    if not latencies_ns:
        return [], []
    
    latencies = np.array(latencies_ns, dtype=np.float64)
    
    if method == "iqr":
        q75 = np.percentile(latencies, 75)
        q25 = np.percentile(latencies, 25)
        iqr = q75 - q25
        lower_bound = q25 - threshold * iqr
        upper_bound = q75 + threshold * iqr
        outlier_mask = (latencies < lower_bound) | (latencies > upper_bound)
    elif method == "zscore":
        mean = np.mean(latencies)
        std = np.std(latencies)
        if std > 0:
            z_scores = np.abs((latencies - mean) / std)
            outlier_mask = z_scores > threshold
        else:
            outlier_mask = np.zeros(len(latencies), dtype=bool)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    outlier_indices = list(np.where(outlier_mask)[0])
    outlier_values = [int(latencies_ns[i]) for i in outlier_indices]
    
    return outlier_indices, outlier_values
