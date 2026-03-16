"""
Mixed load workload runner for realistic deployment scenarios.

Runs inference with configurable background CPU load to simulate
resource contention in real deployments.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.logging_utils import get_logger
from edge_sbc_reliability_lab.inference.common import BenchmarkResult, create_random_input
from edge_sbc_reliability_lab.inference.runtime_interface import get_runtime
from edge_sbc_reliability_lab.workloads.stress_background import BackgroundStressor


@dataclass
class MixedLoadResult:
    """Result from a mixed load benchmark."""
    benchmark_result: BenchmarkResult
    background_load_percent: float
    baseline_comparison: Optional[Dict[str, Any]] = None


class MixedLoadRunner:
    """
    Runner for mixed load benchmarks with background CPU stress.
    
    Simulates realistic deployment conditions where inference
    competes with other workloads for CPU resources.
    """
    
    def __init__(
        self,
        config: ExperimentConfig,
        background_load_percent: float = 25.0,
    ):
        """
        Initialize mixed load runner.
        
        Args:
            config: Experiment configuration
            background_load_percent: Target background CPU load (0-100)
        """
        self.config = config
        self.background_load_percent = min(100, max(0, background_load_percent))
        self.logger = get_logger("MixedLoadRunner")
    
    def run(self) -> MixedLoadResult:
        """
        Run mixed load benchmark.
        
        Returns:
            MixedLoadResult with performance under load
        """
        self.logger.info(
            f"Starting mixed load benchmark with {self.background_load_percent}% background load"
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
        
        # Start background stress
        stressor = BackgroundStressor(target_load_percent=self.background_load_percent)
        stressor.start()
        
        # Wait for stress to stabilize
        time.sleep(2.0)
        
        # Initialize result
        result = BenchmarkResult(
            runtime=self.config.runtime,
            model_name=self.config.model_name,
            model_path=self.config.model_path,
            batch_size=self.config.batch_size,
            threads=self.config.threads,
            warmup_runs=self.config.warmup_runs,
            measured_runs=self.config.measured_runs,
            sustained_duration_sec=self.config.sustained_duration_sec,
        )
        
        latencies = []
        timestamps = []
        
        result.start_time_ns = time.monotonic_ns()
        
        # Run benchmark
        if self.config.sustained_duration_sec > 0:
            duration_ns = int(self.config.sustained_duration_sec * 1e9)
            run_start = time.monotonic_ns()
            
            self.logger.info(f"Running for {self.config.sustained_duration_sec}s under load...")
            
            while (time.monotonic_ns() - run_start) < duration_ns:
                inf_start = time.monotonic_ns()
                runtime.run_inference(input_data)
                inf_end = time.monotonic_ns()
                
                latencies.append(inf_end - inf_start)
                timestamps.append(inf_end - result.start_time_ns)
        else:
            self.logger.info(f"Running {self.config.measured_runs} iterations under load...")
            
            for i in range(self.config.measured_runs):
                inf_start = time.monotonic_ns()
                runtime.run_inference(input_data)
                inf_end = time.monotonic_ns()
                
                latencies.append(inf_end - inf_start)
                timestamps.append(inf_end - result.start_time_ns)
                
                if (i + 1) % (self.config.measured_runs // 10) == 0:
                    self.logger.info(f"Progress: {(i + 1) * 100 // self.config.measured_runs}%")
        
        # Stop background stress
        stressor.stop()
        
        result.end_time_ns = time.monotonic_ns()
        result.total_time_ns = result.end_time_ns - result.start_time_ns
        result.latencies_ns = latencies
        result.timestamps_ns = timestamps
        result.measured_runs = len(latencies)
        result.success = True
        
        runtime.cleanup()
        
        self.logger.info(f"Completed {len(latencies)} inferences under {self.background_load_percent}% load")
        
        return MixedLoadResult(
            benchmark_result=result,
            background_load_percent=self.background_load_percent,
        )


def run_mixed_load_benchmark(
    config: ExperimentConfig,
    background_load_percent: float = 25.0,
) -> MixedLoadResult:
    """
    Convenience function to run a mixed load benchmark.
    
    Args:
        config: Experiment configuration
        background_load_percent: Target background CPU load
        
    Returns:
        MixedLoadResult
    """
    runner = MixedLoadRunner(config, background_load_percent)
    return runner.run()


def run_load_comparison(
    config: ExperimentConfig,
    load_levels: List[float] = None,
) -> List[MixedLoadResult]:
    """
    Run benchmarks at multiple load levels for comparison.
    
    Args:
        config: Experiment configuration
        load_levels: List of background load percentages
        
    Returns:
        List of MixedLoadResult for each load level
    """
    if load_levels is None:
        load_levels = [0, 25, 50, 75]
    
    logger = get_logger("LoadComparison")
    results = []
    
    for load in load_levels:
        logger.info(f"Running benchmark at {load}% background load...")
        
        if load == 0:
            # Run without background load
            from edge_sbc_reliability_lab.workloads.burst_runner import BurstRunner
            runner = BurstRunner(config)
            burst_result = runner.run()
            results.append(MixedLoadResult(
                benchmark_result=burst_result.benchmark_result,
                background_load_percent=0,
            ))
        else:
            runner = MixedLoadRunner(config, load)
            results.append(runner.run())
        
        # Cool down between runs
        logger.info("Cooling down for 30 seconds...")
        time.sleep(30)
    
    return results
