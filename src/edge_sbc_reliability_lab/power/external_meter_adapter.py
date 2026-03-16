"""
External power meter adapter for importing real power measurements.

Supports importing power traces from external USB power meters,
smart plugs, or lab instrumentation in CSV format.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ExternalPowerTrace:
    """External power measurement trace."""
    timestamps_sec: List[float]
    power_watts: List[float]
    source: str
    sample_rate_hz: float
    metadata: Dict


def load_external_power_trace(
    csv_path: str,
    timestamp_col: str = "timestamp",
    power_col: str = "power_watts",
    timestamp_unit: str = "seconds",
    delimiter: str = ",",
) -> ExternalPowerTrace:
    """
    Load external power trace from CSV file.
    
    Expected CSV format:
    timestamp,power_watts
    0.0,3.2
    0.1,4.5
    ...
    
    Args:
        csv_path: Path to CSV file
        timestamp_col: Name of timestamp column
        power_col: Name of power column
        timestamp_unit: Unit of timestamps ("seconds", "milliseconds", "microseconds")
        delimiter: CSV delimiter
        
    Returns:
        ExternalPowerTrace with loaded data
    """
    df = pd.read_csv(csv_path, delimiter=delimiter)
    
    # Get timestamps
    if timestamp_col in df.columns:
        timestamps = df[timestamp_col].values
    else:
        # Try common alternatives
        for col in ["time", "Time", "timestamp_sec", "t"]:
            if col in df.columns:
                timestamps = df[col].values
                break
        else:
            # Assume first column is timestamp
            timestamps = df.iloc[:, 0].values
    
    # Convert timestamp units
    if timestamp_unit == "milliseconds":
        timestamps = timestamps / 1000.0
    elif timestamp_unit == "microseconds":
        timestamps = timestamps / 1e6
    
    # Get power values
    if power_col in df.columns:
        power = df[power_col].values
    else:
        # Try common alternatives
        for col in ["power", "Power", "watts", "Watts", "W"]:
            if col in df.columns:
                power = df[col].values
                break
        else:
            # Assume second column is power
            power = df.iloc[:, 1].values
    
    # Calculate sample rate
    if len(timestamps) > 1:
        intervals = np.diff(timestamps)
        avg_interval = np.mean(intervals)
        sample_rate = 1.0 / avg_interval if avg_interval > 0 else 0
    else:
        sample_rate = 0
    
    return ExternalPowerTrace(
        timestamps_sec=list(timestamps),
        power_watts=list(power),
        source=str(csv_path),
        sample_rate_hz=sample_rate,
        metadata={
            "file": str(csv_path),
            "samples": len(timestamps),
            "duration_sec": timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0,
        }
    )


def align_power_trace(
    power_trace: ExternalPowerTrace,
    benchmark_start_sec: float,
    benchmark_end_sec: float,
    trace_start_offset_sec: float = 0.0,
) -> ExternalPowerTrace:
    """
    Align external power trace with benchmark timing.
    
    Args:
        power_trace: Original power trace
        benchmark_start_sec: Benchmark start time (relative to trace start)
        benchmark_end_sec: Benchmark end time (relative to trace start)
        trace_start_offset_sec: Offset to apply to trace timestamps
        
    Returns:
        Aligned power trace covering only the benchmark period
    """
    timestamps = np.array(power_trace.timestamps_sec) + trace_start_offset_sec
    power = np.array(power_trace.power_watts)
    
    # Find indices within benchmark window
    mask = (timestamps >= benchmark_start_sec) & (timestamps <= benchmark_end_sec)
    
    aligned_timestamps = timestamps[mask] - benchmark_start_sec  # Normalize to 0
    aligned_power = power[mask]
    
    return ExternalPowerTrace(
        timestamps_sec=list(aligned_timestamps),
        power_watts=list(aligned_power),
        source=power_trace.source,
        sample_rate_hz=power_trace.sample_rate_hz,
        metadata={
            **power_trace.metadata,
            "aligned": True,
            "benchmark_start_sec": benchmark_start_sec,
            "benchmark_end_sec": benchmark_end_sec,
        }
    )


def compute_trace_statistics(trace: ExternalPowerTrace) -> Dict:
    """
    Compute statistics from power trace.
    
    Args:
        trace: Power trace
        
    Returns:
        Dictionary with power statistics
    """
    if not trace.power_watts:
        return {
            "is_external_measurement": True,
            "mean_watts": 0.0,
            "min_watts": 0.0,
            "max_watts": 0.0,
            "std_watts": 0.0,
            "total_energy_joules": 0.0,
            "duration_sec": 0.0,
            "sample_count": 0,
        }
    
    power = np.array(trace.power_watts)
    timestamps = np.array(trace.timestamps_sec)
    
    # Energy calculation using trapezoidal integration
    if len(timestamps) > 1:
        energy = np.trapz(power, timestamps)
        duration = timestamps[-1] - timestamps[0]
    else:
        energy = 0
        duration = 0
    
    return {
        "is_external_measurement": True,
        "source": trace.source,
        "mean_watts": float(np.mean(power)),
        "min_watts": float(np.min(power)),
        "max_watts": float(np.max(power)),
        "std_watts": float(np.std(power)),
        "total_energy_joules": float(energy),
        "duration_sec": float(duration),
        "sample_count": len(power),
        "sample_rate_hz": trace.sample_rate_hz,
    }


def validate_power_trace(trace: ExternalPowerTrace) -> Tuple[bool, List[str]]:
    """
    Validate power trace data quality.
    
    Args:
        trace: Power trace to validate
        
    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True
    
    if not trace.power_watts:
        return False, ["Power trace is empty"]
    
    power = np.array(trace.power_watts)
    
    # Check for negative values
    if np.any(power < 0):
        warnings.append("Power trace contains negative values")
    
    # Check for unreasonably high values (> 50W for Pi)
    if np.any(power > 50):
        warnings.append("Power trace contains values > 50W (unusual for Raspberry Pi)")
    
    # Check for gaps in timestamps
    if len(trace.timestamps_sec) > 1:
        intervals = np.diff(trace.timestamps_sec)
        expected_interval = 1.0 / trace.sample_rate_hz if trace.sample_rate_hz > 0 else np.mean(intervals)
        
        if np.any(intervals > expected_interval * 3):
            warnings.append("Power trace has gaps in sampling")
    
    # Check sample count
    if len(trace.power_watts) < 10:
        warnings.append("Power trace has very few samples")
    
    return is_valid, warnings


def interpolate_power_to_latencies(
    power_trace: ExternalPowerTrace,
    latency_timestamps_sec: List[float],
) -> List[float]:
    """
    Interpolate power values to latency measurement timestamps.
    
    Args:
        power_trace: Power trace
        latency_timestamps_sec: Timestamps of latency measurements
        
    Returns:
        List of interpolated power values
    """
    if not power_trace.power_watts or not latency_timestamps_sec:
        return []
    
    return list(np.interp(
        latency_timestamps_sec,
        power_trace.timestamps_sec,
        power_trace.power_watts,
    ))
