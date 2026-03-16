"""Thermal behavior monitoring module."""

from edge_sbc_reliability_lab.thermal.temp_logger import (
    TempLogger,
    get_cpu_temperature,
)
from edge_sbc_reliability_lab.thermal.freq_logger import (
    FreqLogger,
    get_cpu_frequency,
)
from edge_sbc_reliability_lab.thermal.throttle_detector import (
    ThrottleDetector,
    detect_throttling,
)
from edge_sbc_reliability_lab.thermal.drift_analysis import (
    analyze_thermal_drift,
    compute_latency_temp_correlation,
)

__all__ = [
    "TempLogger",
    "get_cpu_temperature",
    "FreqLogger",
    "get_cpu_frequency",
    "ThrottleDetector",
    "detect_throttling",
    "analyze_thermal_drift",
    "compute_latency_temp_correlation",
]
