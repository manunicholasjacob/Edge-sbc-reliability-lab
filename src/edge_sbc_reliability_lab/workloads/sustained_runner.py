"""
Sustained workload runner for long-duration benchmarks.

Runs inference continuously for a specified duration to measure
thermal drift, performance stability, and sustained throughput.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.logging_utils import get_logger, ProgressLogger
from edge_sbc_reliability_lab.inference.common import BenchmarkResult, create_random_input
from edge_sbc_reliability_lab.inference.runtime_interface import get_runtime


@dataclass
class SustainedRunResult:
    """Result from a sustained benchmark run."""
    benchmark_result: BenchmarkResult
    phases: List[Dict[str, Any]] = field(default_factory=list)
    phase_duration_sec: float = 60.0
    total_phases: int = 0


class SustainedRunner:
    """
    Runner for sustained duration benchmarks.
    
    Divides the benchmark into phases for analysis of performance
    changes over time.
    """
    
    def __init__(
        self,
        config: ExperimentConfig,
        phase_duration_sec: float = 60.0,
    ):
        """
        Initialize sustained runner.
        
        Args:
            config: Experiment configuration
            phase_duration_sec: Duration of each analysis phase
        """
        self.config = config
        self.phase_duration_sec = phase_duration_sec
        self.logger = get_logger("SustainedRunner")
    
    def run(self) -> SustainedRunResult:
        """
        Run sustained benchmark.
        
        Returns:
            SustainedRunResult with detailed phase analysis
        """
        total_duration = self.config.sustained_duration_sec
        if total_duration <= 0:
            total_duration = 600  # Default 10 minutes
        
        num_phases = max(1, int(total_duration / self.phase_duration_sec))
        
        self.logger.info(
            f"Starting sustained benchmark: {total_duration}s total, "
            f"{num_phases} phases of {self.phase_duration_sec}s each"
        )
        
        # Initialize runtime
        runtime = get_runtime(self.config.runtime)
        runtime.set_threads(self.config.threads)
        runtime.load_model(self.config.model_path, input_shape=self.config.input_shape)
        
        # Get input shape and create input
        input_shape = self.config.input_shape or runtime.get_input_shape()
        if input_shape[0] != self.config.batch_size:
            input_shape = [self.config.batch_size] + list(input_shape[1:])
        
        input_data = create_random_input(input_shape, self.config.input_dtype, seed=42)
        
        # Warmup
        self.logger.info(f"Running {self.config.warmup_runs} warmup iterations...")
        for _ in range(self.config.warmup_runs):
            runtime.run_inference(input_data)
        
        # Initialize result
        result = BenchmarkResult(
            runtime=self.config.runtime,
            model_name=self.config.model_name,
            model_path=self.config.model_path,
            batch_size=self.config.batch_size,
            threads=self.config.threads,
            warmup_runs=self.config.warmup_runs,
            measured_runs=0,
            sustained_duration_sec=total_duration,
        )
        
        all_latencies = []
        all_timestamps = []
        phases = []
        
        result.start_time_ns = time.monotonic_ns()
        
        # Progress tracking
        progress = ProgressLogger(
            total=num_phases,
            logger=self.logger,
            prefix="Sustained run",
            update_interval=20,
        )
        
        # Run phases
        for phase_idx in range(num_phases):
            phase_start = time.monotonic_ns()
            phase_latencies = []
            phase_timestamps = []
            
            phase_duration_ns = int(self.phase_duration_sec * 1e9)
            
            while (time.monotonic_ns() - phase_start) < phase_duration_ns:
                inf_start = time.monotonic_ns()
                runtime.run_inference(input_data)
                inf_end = time.monotonic_ns()
                
                latency_ns = inf_end - inf_start
                timestamp_ns = inf_end - result.start_time_ns
                
                phase_latencies.append(latency_ns)
                phase_timestamps.append(timestamp_ns)
                
                if self.config.inter_inference_delay_ms > 0:
                    time.sleep(self.config.inter_inference_delay_ms / 1000.0)
            
            # Store phase data
            all_latencies.extend(phase_latencies)
            all_timestamps.extend(phase_timestamps)
            
            # Compute phase statistics
            if phase_latencies:
                import numpy as np
                latencies_ms = np.array(phase_latencies) / 1e6
                
                phases.append({
                    "phase": phase_idx + 1,
                    "start_sec": phase_timestamps[0] / 1e9 if phase_timestamps else 0,
                    "end_sec": phase_timestamps[-1] / 1e9 if phase_timestamps else 0,
                    "count": len(phase_latencies),
                    "mean_ms": float(np.mean(latencies_ms)),
                    "p50_ms": float(np.percentile(latencies_ms, 50)),
                    "p99_ms": float(np.percentile(latencies_ms, 99)),
                    "throughput": len(phase_latencies) / self.phase_duration_sec,
                })
            
            progress.update(1)
        
        progress.finish()
        
        # Finalize result
        result.end_time_ns = time.monotonic_ns()
        result.total_time_ns = result.end_time_ns - result.start_time_ns
        result.latencies_ns = all_latencies
        result.timestamps_ns = all_timestamps
        result.measured_runs = len(all_latencies)
        result.success = True
        
        runtime.cleanup()
        
        self.logger.info(f"Completed {len(all_latencies)} inferences in {num_phases} phases")
        
        return SustainedRunResult(
            benchmark_result=result,
            phases=phases,
            phase_duration_sec=self.phase_duration_sec,
            total_phases=num_phases,
        )


def run_sustained_benchmark(
    config: ExperimentConfig,
    duration_sec: float = 600,
    phase_duration_sec: float = 60,
) -> SustainedRunResult:
    """
    Convenience function to run a sustained benchmark.
    
    Args:
        config: Experiment configuration
        duration_sec: Total duration in seconds
        phase_duration_sec: Duration of each phase
        
    Returns:
        SustainedRunResult
    """
    config.sustained_duration_sec = duration_sec
    runner = SustainedRunner(config, phase_duration_sec)
    return runner.run()
