#!/usr/bin/env python3
"""
TensorFlow Lite inference benchmark runner.

Provides CLI and programmatic interface for benchmarking TFLite models
on Raspberry Pi 5.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from edge_sbc_reliability_lab.inference.common import (
    BenchmarkResult,
    create_random_input,
    run_measured_iterations,
    run_sustained_duration,
    run_warmup,
)
from edge_sbc_reliability_lab.inference.runtime_interface import TFLiteRuntime


def run_tflite_benchmark(
    model_path: str,
    warmup_runs: int = 10,
    measured_runs: int = 100,
    sustained_duration_sec: float = 0.0,
    batch_size: int = 1,
    threads: int = 4,
    input_shape: Optional[List[int]] = None,
    input_dtype: str = "float32",
    inter_delay_ms: float = 0.0,
) -> BenchmarkResult:
    """
    Run TensorFlow Lite benchmark.
    
    Args:
        model_path: Path to TFLite model file
        warmup_runs: Number of warmup iterations
        measured_runs: Number of measured iterations (if not using sustained mode)
        sustained_duration_sec: Duration for sustained mode (0 = use measured_runs)
        batch_size: Batch size for inference
        threads: Number of threads
        input_shape: Input shape (auto-detected if None)
        input_dtype: Input data type
        inter_delay_ms: Delay between inferences
        
    Returns:
        BenchmarkResult with all measurements
    """
    result = BenchmarkResult(
        runtime="tflite",
        model_name=Path(model_path).stem,
        model_path=model_path,
        batch_size=batch_size,
        threads=threads,
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
        sustained_duration_sec=sustained_duration_sec,
    )
    
    try:
        # Initialize runtime
        runtime = TFLiteRuntime()
        runtime.set_threads(threads)
        runtime.load_model(model_path)
        
        # Get input shape
        if input_shape is None:
            input_shape = runtime.get_input_shape()
        
        # Get input dtype from model
        model_dtype = runtime.get_input_dtype()
        
        # Create input data
        input_data = create_random_input(input_shape, model_dtype, seed=42)
        
        # Warmup
        run_warmup(runtime.run_inference, warmup_runs, input_data)
        
        # Record start time
        result.start_time_ns = time.monotonic_ns()
        
        # Run benchmark
        if sustained_duration_sec > 0:
            latencies, timestamps = run_sustained_duration(
                runtime.run_inference,
                sustained_duration_sec,
                result.start_time_ns,
                inter_delay_ms,
                input_data
            )
        else:
            latencies, timestamps = run_measured_iterations(
                runtime.run_inference,
                measured_runs,
                result.start_time_ns,
                inter_delay_ms,
                input_data
            )
        
        # Record end time
        result.end_time_ns = time.monotonic_ns()
        result.total_time_ns = result.end_time_ns - result.start_time_ns
        
        # Store results
        result.latencies_ns = latencies
        result.timestamps_ns = timestamps
        result.success = True
        
        # Cleanup
        runtime.cleanup()
        
    except Exception as e:
        result.success = False
        result.errors.append(str(e))
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TensorFlow Lite inference benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "model_path",
        help="Path to TFLite model file"
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=10,
        help="Number of warmup runs"
    )
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=100,
        help="Number of measured runs"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=0.0,
        help="Sustained duration in seconds (overrides --runs)"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=1,
        help="Batch size"
    )
    parser.add_argument(
        "--threads", "-t",
        type=int,
        default=4,
        help="Number of threads"
    )
    parser.add_argument(
        "--input-shape",
        type=str,
        default=None,
        help="Input shape as comma-separated values (e.g., 1,224,224,3)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file for results (JSON)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output"
    )
    
    args = parser.parse_args()
    
    # Parse input shape
    input_shape = None
    if args.input_shape:
        input_shape = [int(x) for x in args.input_shape.split(",")]
    
    # Run benchmark
    result = run_tflite_benchmark(
        model_path=args.model_path,
        warmup_runs=args.warmup,
        measured_runs=args.runs,
        sustained_duration_sec=args.duration,
        batch_size=args.batch_size,
        threads=args.threads,
        input_shape=input_shape,
    )
    
    if not args.quiet:
        # Print summary
        from edge_sbc_reliability_lab.core.statistics import compute_latency_stats
        
        stats = compute_latency_stats(result.latencies_ns, result.total_time_ns)
        
        print(f"\n{'='*60}")
        print(f"TensorFlow Lite Benchmark Results")
        print(f"{'='*60}")
        print(f"Model: {result.model_name}")
        print(f"Runtime: {result.runtime}")
        print(f"Batch size: {result.batch_size}")
        print(f"Threads: {result.threads}")
        print(f"{'='*60}")
        print(f"Total inferences: {stats.count}")
        print(f"Total time: {stats.total_time_sec:.2f}s")
        print(f"Throughput: {stats.throughput_infs_per_sec:.2f} inf/s")
        print(f"{'='*60}")
        print(f"Mean latency: {stats.mean_ms:.3f} ms")
        print(f"Median latency: {stats.median_ms:.3f} ms")
        print(f"Std deviation: {stats.std_ms:.3f} ms")
        print(f"Min latency: {stats.min_ms:.3f} ms")
        print(f"Max latency: {stats.max_ms:.3f} ms")
        print(f"{'='*60}")
        print(f"P50: {stats.p50_ms:.3f} ms")
        print(f"P90: {stats.p90_ms:.3f} ms")
        print(f"P95: {stats.p95_ms:.3f} ms")
        print(f"P99: {stats.p99_ms:.3f} ms")
        print(f"{'='*60}")
    
    # Save results if requested
    if args.output:
        import json
        output_data = {
            "benchmark": result.to_dict(),
            "latencies_ms": [l / 1e6 for l in result.latencies_ns],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        if not args.quiet:
            print(f"Results saved to: {args.output}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
