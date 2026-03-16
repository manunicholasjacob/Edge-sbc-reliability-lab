"""
Energy analysis utilities.

Computes energy metrics from power measurements or proxy estimates.
"""

from typing import Dict, List, Optional

import numpy as np


def compute_energy_metrics(
    power_watts: List[float],
    timestamps_sec: List[float],
    total_inferences: int,
) -> Dict:
    """
    Compute energy metrics from power data.
    
    Args:
        power_watts: Power measurements or estimates in watts
        timestamps_sec: Timestamps in seconds
        total_inferences: Total number of inferences performed
        
    Returns:
        Dictionary with energy metrics
    """
    if not power_watts or len(power_watts) < 2:
        return {
            "total_energy_joules": 0.0,
            "mean_power_watts": 0.0,
            "energy_per_inference_mj": 0.0,
            "duration_sec": 0.0,
        }
    
    power = np.array(power_watts)
    times = np.array(timestamps_sec)
    
    # Total energy using trapezoidal integration
    total_energy = np.trapz(power, times)
    
    # Duration
    duration = times[-1] - times[0]
    
    # Mean power
    mean_power = float(np.mean(power))
    
    # Energy per inference (in millijoules)
    if total_inferences > 0:
        energy_per_inf_j = total_energy / total_inferences
        energy_per_inf_mj = energy_per_inf_j * 1000
    else:
        energy_per_inf_mj = 0.0
    
    return {
        "total_energy_joules": float(total_energy),
        "mean_power_watts": mean_power,
        "energy_per_inference_mj": energy_per_inf_mj,
        "energy_per_inference_j": float(total_energy / total_inferences) if total_inferences > 0 else 0.0,
        "duration_sec": float(duration),
        "sample_count": len(power),
    }


def compute_energy_per_inference(
    power_watts: List[float],
    power_timestamps_sec: List[float],
    latency_timestamps_sec: List[float],
    latencies_ms: List[float],
) -> Dict:
    """
    Compute per-inference energy estimates.
    
    Aligns power measurements with inference timestamps to estimate
    energy consumption for each inference.
    
    Args:
        power_watts: Power measurements
        power_timestamps_sec: Timestamps of power measurements
        latency_timestamps_sec: Timestamps when inferences completed
        latencies_ms: Latency of each inference in milliseconds
        
    Returns:
        Dictionary with per-inference energy analysis
    """
    if not power_watts or not latencies_ms:
        return {
            "mean_energy_per_inference_mj": 0.0,
            "min_energy_per_inference_mj": 0.0,
            "max_energy_per_inference_mj": 0.0,
            "total_inferences": 0,
        }
    
    # Interpolate power to inference timestamps
    power_at_inference = np.interp(
        latency_timestamps_sec,
        power_timestamps_sec,
        power_watts,
    )
    
    # Estimate energy for each inference: E = P * t
    latencies_sec = np.array(latencies_ms) / 1000.0
    energy_per_inf_j = power_at_inference * latencies_sec
    energy_per_inf_mj = energy_per_inf_j * 1000
    
    return {
        "mean_energy_per_inference_mj": float(np.mean(energy_per_inf_mj)),
        "median_energy_per_inference_mj": float(np.median(energy_per_inf_mj)),
        "min_energy_per_inference_mj": float(np.min(energy_per_inf_mj)),
        "max_energy_per_inference_mj": float(np.max(energy_per_inf_mj)),
        "std_energy_per_inference_mj": float(np.std(energy_per_inf_mj)),
        "total_energy_mj": float(np.sum(energy_per_inf_mj)),
        "total_inferences": len(latencies_ms),
    }


def compute_efficiency_metrics(
    throughput_infs_per_sec: float,
    mean_power_watts: float,
    mean_latency_ms: float,
) -> Dict:
    """
    Compute efficiency metrics.
    
    Args:
        throughput_infs_per_sec: Inference throughput
        mean_power_watts: Mean power consumption
        mean_latency_ms: Mean inference latency
        
    Returns:
        Dictionary with efficiency metrics
    """
    # Inferences per joule
    if mean_power_watts > 0:
        infs_per_joule = throughput_infs_per_sec / mean_power_watts
    else:
        infs_per_joule = 0.0
    
    # Energy-delay product (lower is better)
    # EDP = Energy * Latency = Power * Latency^2
    mean_latency_sec = mean_latency_ms / 1000.0
    edp = mean_power_watts * (mean_latency_sec ** 2)
    
    # Performance per watt
    perf_per_watt = throughput_infs_per_sec / mean_power_watts if mean_power_watts > 0 else 0
    
    return {
        "inferences_per_joule": infs_per_joule,
        "energy_delay_product": edp,
        "performance_per_watt": perf_per_watt,
        "throughput_infs_per_sec": throughput_infs_per_sec,
        "mean_power_watts": mean_power_watts,
        "mean_latency_ms": mean_latency_ms,
    }


def estimate_battery_runtime(
    mean_power_watts: float,
    battery_capacity_wh: float,
    efficiency: float = 0.85,
) -> Dict:
    """
    Estimate battery runtime for edge deployment.
    
    Args:
        mean_power_watts: Mean power consumption during inference
        battery_capacity_wh: Battery capacity in watt-hours
        efficiency: Power conversion efficiency (default 85%)
        
    Returns:
        Dictionary with battery runtime estimates
    """
    if mean_power_watts <= 0:
        return {
            "runtime_hours": 0.0,
            "runtime_minutes": 0.0,
            "total_inferences_estimate": 0,
        }
    
    # Effective capacity after efficiency loss
    effective_capacity = battery_capacity_wh * efficiency
    
    # Runtime in hours
    runtime_hours = effective_capacity / mean_power_watts
    runtime_minutes = runtime_hours * 60
    
    return {
        "runtime_hours": runtime_hours,
        "runtime_minutes": runtime_minutes,
        "battery_capacity_wh": battery_capacity_wh,
        "mean_power_watts": mean_power_watts,
        "efficiency": efficiency,
    }
