"""
Burst workload runner for short, intensive benchmarks.

Runs a fixed number of inferences as fast as possible to measure
peak performance characteristics.
"""

import time
from dataclasses import dataclass
from typing import List, Optional

from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.logging_utils import get_logger
from edge_sbc_reliability_lab.inference.common import BenchmarkResult, create_random_input
from edge_sbc_reliability_lab.inference.runtime_interface import get_runtime


@dataclass
class BurstRunResult:
    """Result from a burst benchmark run."""
    benchmark_result: BenchmarkResult
    burst_throughput: float  # Peak throughput during burst
    warmup_latencies_ns: List[int]


class BurstRunner:
    """
    Runner for burst/peak performance benchmarks.
    
    Runs inferences as fast as possible without delays to measure
    maximum achievable throughput.
    """
    
    def __init__(self, config: ExperimentConfig):
        """
        Initialize burst runner.
        
        Args:
            config: Experiment configuration
        """
        self.config = config
        self.logger = get_logger("BurstRunner")
    
    def run(self) -> BurstRunResult:
        """
        Run burst benchmark.
        
        Returns:
            BurstRunResult with peak performance metrics
        """
        num_runs = self.config.measured_runs
        if num_runs <= 0:
            num_runs = 1000  # Default for burst mode
        
        self.logger.info(f"Starting burst benchmark: {num_runs} iterations")
        
        # Initialize runtime
        runtime = get_runtime(self.config.runtime)
        runtime.set_threads(self.config.threads)
        runtime.load_model(self.config.model_path, input_shape=self.config.input_shape)
        
        # Get input shape and create input
        input_shape = self.config.input_shape or runtime.get_input_shape()
        if input_shape[0] != self.config.batch_size:
            input_shape = [self.config.batch_size] + list(input_shape[1:])
        
        input_data = create_random_input(input_shape, self.config.input_dtype, seed=42)
        
        # Warmup with timing
        self.logger.info(f"Running {self.config.warmup_runs} warmup iterations...")
        warmup_latencies = []
        for _ in range(self.config.warmup_runs):
            start = time.monotonic_ns()
            runtime.run_inference(input_data)
            end = time.monotonic_ns()
            warmup_latencies.append(end - start)
        
        # Initialize result
        result = BenchmarkResult(
            runtime=self.config.runtime,
            model_name=self.config.model_name,
            model_path=self.config.model_path,
            batch_size=self.config.batch_size,
            threads=self.config.threads,
            warmup_runs=self.config.warmup_runs,
            measured_runs=num_runs,
            sustained_duration_sec=0,
        )
        
        latencies = []
        timestamps = []
        
        # Run burst - no delays, maximum speed
        self.logger.info(f"Running {num_runs} burst iterations...")
        result.start_time_ns = time.monotonic_ns()
        
        for i in range(num_runs):
            inf_start = time.monotonic_ns()
            runtime.run_inference(input_data)
            inf_end = time.monotonic_ns()
            
            latencies.append(inf_end - inf_start)
            timestamps.append(inf_end - result.start_time_ns)
            
            # Log progress every 10%
            if (i + 1) % (num_runs // 10) == 0:
                self.logger.info(f"Progress: {(i + 1) * 100 // num_runs}%")
        
        result.end_time_ns = time.monotonic_ns()
        result.total_time_ns = result.end_time_ns - result.start_time_ns
        result.latencies_ns = latencies
        result.timestamps_ns = timestamps
        result.success = True
        
        runtime.cleanup()
        
        # Calculate burst throughput
        burst_throughput = num_runs / (result.total_time_ns / 1e9)
        
        self.logger.info(
            f"Burst complete: {num_runs} inferences in "
            f"{result.total_time_ns / 1e9:.2f}s ({burst_throughput:.1f} inf/s)"
        )
        
        return BurstRunResult(
            benchmark_result=result,
            burst_throughput=burst_throughput,
            warmup_latencies_ns=warmup_latencies,
        )


def run_burst_benchmark(
    config: ExperimentConfig,
    num_iterations: int = 1000,
) -> BurstRunResult:
    """
    Convenience function to run a burst benchmark.
    
    Args:
        config: Experiment configuration
        num_iterations: Number of iterations
        
    Returns:
        BurstRunResult
    """
    config.measured_runs = num_iterations
    config.sustained_duration_sec = 0
    runner = BurstRunner(config)
    return runner.run()
