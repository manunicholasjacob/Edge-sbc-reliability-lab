"""Workload modes for different benchmark scenarios."""

from edge_sbc_reliability_lab.workloads.sustained_runner import (
    SustainedRunner,
    run_sustained_benchmark,
)
from edge_sbc_reliability_lab.workloads.burst_runner import (
    BurstRunner,
    run_burst_benchmark,
)
from edge_sbc_reliability_lab.workloads.mixed_load_runner import (
    MixedLoadRunner,
    run_mixed_load_benchmark,
)
from edge_sbc_reliability_lab.workloads.stress_background import (
    BackgroundStressor,
    start_cpu_stress,
    stop_cpu_stress,
)

__all__ = [
    "SustainedRunner",
    "run_sustained_benchmark",
    "BurstRunner",
    "run_burst_benchmark",
    "MixedLoadRunner",
    "run_mixed_load_benchmark",
    "BackgroundStressor",
    "start_cpu_stress",
    "stop_cpu_stress",
]
