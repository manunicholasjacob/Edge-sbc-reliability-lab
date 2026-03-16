"""
Edge SBC Reliability Lab

A reproducible benchmarking and reliability framework for AI inference
on Raspberry Pi 5 and similar single-board computers.

This package provides tools for:
- Multi-runtime inference benchmarking (ONNX, TFLite, PyTorch)
- Thermal behavior monitoring and drift analysis
- Sustained workload testing
- Power proxy estimation
- Publication-ready result generation
"""

__version__ = "1.0.0"
__author__ = "Manu Nicholas Jacob"

from edge_sbc_reliability_lab.core.config import ExperimentConfig, load_config
from edge_sbc_reliability_lab.core.runner import BenchmarkRunner, run_benchmark
from edge_sbc_reliability_lab.core.statistics import compute_latency_stats, LatencyStats
from edge_sbc_reliability_lab.inference.runtime_interface import (
    get_runtime,
    list_available_runtimes,
)

__all__ = [
    "__version__",
    "ExperimentConfig",
    "load_config",
    "BenchmarkRunner",
    "run_benchmark",
    "compute_latency_stats",
    "LatencyStats",
    "get_runtime",
    "list_available_runtimes",
]
