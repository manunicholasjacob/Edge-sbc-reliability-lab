"""
Common utilities for inference benchmarking.

Provides shared data structures and helper functions for all runtimes.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class InferenceResult:
    """Result of a single inference."""
    latency_ns: int
    timestamp_ns: int  # Monotonic time when inference completed
    success: bool = True
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    
    # Identification
    runtime: str
    model_name: str
    model_path: str
    
    # Configuration
    batch_size: int
    threads: int
    warmup_runs: int
    measured_runs: int
    sustained_duration_sec: float
    
    # Raw data
    latencies_ns: List[int] = field(default_factory=list)
    timestamps_ns: List[int] = field(default_factory=list)
    
    # Timing
    start_time_ns: int = 0
    end_time_ns: int = 0
    total_time_ns: int = 0
    
    # Status
    success: bool = True
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding raw latency arrays for summary)."""
        return {
            "runtime": self.runtime,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "batch_size": self.batch_size,
            "threads": self.threads,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
            "sustained_duration_sec": self.sustained_duration_sec,
            "total_inferences": len(self.latencies_ns),
            "total_time_sec": self.total_time_ns / 1e9,
            "success": self.success,
            "error_count": len(self.errors),
        }


def create_random_input(
    shape: List[int],
    dtype: str = "float32",
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Create random input tensor for inference.
    
    Args:
        shape: Input tensor shape (e.g., [1, 3, 224, 224])
        dtype: Data type string
        seed: Optional random seed for reproducibility
        
    Returns:
        NumPy array with random values
    """
    if seed is not None:
        np.random.seed(seed)
    
    dtype_map = {
        "float32": np.float32,
        "float16": np.float16,
        "int8": np.int8,
        "uint8": np.uint8,
        "int32": np.int32,
        "int64": np.int64,
    }
    
    np_dtype = dtype_map.get(dtype, np.float32)
    
    if np_dtype in (np.float32, np.float16):
        # Random floats in [0, 1]
        return np.random.rand(*shape).astype(np_dtype)
    elif np_dtype == np.uint8:
        # Random integers in [0, 255] (typical for image input)
        return np.random.randint(0, 256, size=shape, dtype=np_dtype)
    elif np_dtype == np.int8:
        # Random integers in [-128, 127]
        return np.random.randint(-128, 128, size=shape, dtype=np_dtype)
    else:
        # Random integers
        return np.random.randint(0, 100, size=shape, dtype=np_dtype)


def measure_inference(
    inference_fn,
    *args,
    **kwargs
) -> Tuple[int, Any]:
    """
    Measure inference latency with high precision.
    
    Args:
        inference_fn: Function to measure
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function
        
    Returns:
        Tuple of (latency_ns, result)
    """
    start = time.monotonic_ns()
    result = inference_fn(*args, **kwargs)
    end = time.monotonic_ns()
    return end - start, result


def run_warmup(
    inference_fn,
    n_runs: int,
    *args,
    **kwargs
) -> List[int]:
    """
    Run warmup inferences.
    
    Args:
        inference_fn: Inference function
        n_runs: Number of warmup runs
        *args: Arguments for inference function
        **kwargs: Keyword arguments for inference function
        
    Returns:
        List of warmup latencies in nanoseconds
    """
    latencies = []
    for _ in range(n_runs):
        latency_ns, _ = measure_inference(inference_fn, *args, **kwargs)
        latencies.append(latency_ns)
    return latencies


def run_measured_iterations(
    inference_fn,
    n_runs: int,
    start_time_ns: int,
    inter_delay_ms: float = 0.0,
    *args,
    **kwargs
) -> Tuple[List[int], List[int]]:
    """
    Run measured inference iterations.
    
    Args:
        inference_fn: Inference function
        n_runs: Number of measured runs
        start_time_ns: Benchmark start time for timestamps
        inter_delay_ms: Delay between inferences in milliseconds
        *args: Arguments for inference function
        **kwargs: Keyword arguments for inference function
        
    Returns:
        Tuple of (latencies_ns, timestamps_ns)
    """
    latencies = []
    timestamps = []
    
    for _ in range(n_runs):
        latency_ns, _ = measure_inference(inference_fn, *args, **kwargs)
        timestamp_ns = time.monotonic_ns() - start_time_ns
        
        latencies.append(latency_ns)
        timestamps.append(timestamp_ns)
        
        if inter_delay_ms > 0:
            time.sleep(inter_delay_ms / 1000.0)
    
    return latencies, timestamps


def run_sustained_duration(
    inference_fn,
    duration_sec: float,
    start_time_ns: int,
    inter_delay_ms: float = 0.0,
    *args,
    **kwargs
) -> Tuple[List[int], List[int]]:
    """
    Run inferences for a sustained duration.
    
    Args:
        inference_fn: Inference function
        duration_sec: Duration to run in seconds
        start_time_ns: Benchmark start time for timestamps
        inter_delay_ms: Delay between inferences in milliseconds
        *args: Arguments for inference function
        **kwargs: Keyword arguments for inference function
        
    Returns:
        Tuple of (latencies_ns, timestamps_ns)
    """
    latencies = []
    timestamps = []
    
    duration_ns = int(duration_sec * 1e9)
    run_start = time.monotonic_ns()
    
    while (time.monotonic_ns() - run_start) < duration_ns:
        latency_ns, _ = measure_inference(inference_fn, *args, **kwargs)
        timestamp_ns = time.monotonic_ns() - start_time_ns
        
        latencies.append(latency_ns)
        timestamps.append(timestamp_ns)
        
        if inter_delay_ms > 0:
            time.sleep(inter_delay_ms / 1000.0)
    
    return latencies, timestamps


def validate_model_path(path: str) -> Tuple[bool, str]:
    """
    Validate that a model file exists and has correct extension.
    
    Args:
        path: Path to model file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from pathlib import Path
    
    model_path = Path(path)
    
    if not model_path.exists():
        return False, f"Model file not found: {path}"
    
    if not model_path.is_file():
        return False, f"Model path is not a file: {path}"
    
    valid_extensions = {".onnx", ".tflite", ".pt", ".pth", ".pb"}
    if model_path.suffix.lower() not in valid_extensions:
        return False, f"Unknown model extension: {model_path.suffix}"
    
    return True, ""
