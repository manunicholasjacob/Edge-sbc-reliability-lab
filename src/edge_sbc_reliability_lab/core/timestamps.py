"""
Timestamp management for synchronized telemetry and latency logging.

Provides consistent timestamp generation across all modules for accurate
correlation of inference latencies with thermal and power measurements.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple


@dataclass
class TimestampedSample:
    """A single timestamped measurement."""
    timestamp_ns: int  # Monotonic nanoseconds since start
    wall_time: str     # ISO format wall clock time
    value: float       # The measured value


class TimestampManager:
    """
    Manages synchronized timestamps across benchmark components.
    
    Uses monotonic clock for precise interval measurements and wall clock
    for human-readable timestamps and cross-run correlation.
    """
    
    def __init__(self):
        """Initialize timestamp manager with current time as reference."""
        self._start_monotonic_ns = time.monotonic_ns()
        self._start_wall_time = datetime.now(timezone.utc)
        self._start_wall_iso = self._start_wall_time.isoformat()
    
    @property
    def start_time_iso(self) -> str:
        """Get ISO format start time."""
        return self._start_wall_iso
    
    @property
    def start_time_unix(self) -> float:
        """Get Unix timestamp of start time."""
        return self._start_wall_time.timestamp()
    
    def elapsed_ns(self) -> int:
        """Get nanoseconds elapsed since start."""
        return time.monotonic_ns() - self._start_monotonic_ns
    
    def elapsed_sec(self) -> float:
        """Get seconds elapsed since start."""
        return self.elapsed_ns() / 1e9
    
    def elapsed_ms(self) -> float:
        """Get milliseconds elapsed since start."""
        return self.elapsed_ns() / 1e6
    
    def now_iso(self) -> str:
        """Get current wall clock time in ISO format."""
        return datetime.now(timezone.utc).isoformat()
    
    def now_monotonic_ns(self) -> int:
        """Get current monotonic time in nanoseconds."""
        return time.monotonic_ns()
    
    def get_timestamp_pair(self) -> Tuple[int, str]:
        """
        Get both monotonic elapsed time and wall clock time.
        
        Returns:
            Tuple of (elapsed_ns, wall_time_iso)
        """
        return self.elapsed_ns(), self.now_iso()
    
    def create_sample(self, value: float) -> TimestampedSample:
        """
        Create a timestamped sample with current time.
        
        Args:
            value: The measurement value
            
        Returns:
            TimestampedSample with current timestamps
        """
        elapsed_ns, wall_time = self.get_timestamp_pair()
        return TimestampedSample(
            timestamp_ns=elapsed_ns,
            wall_time=wall_time,
            value=value
        )
    
    @staticmethod
    def measure_latency_ns(func, *args, **kwargs) -> Tuple[int, any]:
        """
        Measure execution time of a function in nanoseconds.
        
        Args:
            func: Function to measure
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Tuple of (latency_ns, return_value)
        """
        start = time.monotonic_ns()
        result = func(*args, **kwargs)
        end = time.monotonic_ns()
        return end - start, result
    
    @staticmethod
    def ns_to_ms(ns: int) -> float:
        """Convert nanoseconds to milliseconds."""
        return ns / 1e6
    
    @staticmethod
    def ns_to_sec(ns: int) -> float:
        """Convert nanoseconds to seconds."""
        return ns / 1e9
    
    @staticmethod
    def ms_to_ns(ms: float) -> int:
        """Convert milliseconds to nanoseconds."""
        return int(ms * 1e6)
    
    @staticmethod
    def sec_to_ns(sec: float) -> int:
        """Convert seconds to nanoseconds."""
        return int(sec * 1e9)


def generate_run_id(prefix: str = "") -> str:
    """
    Generate a unique run identifier based on current timestamp.
    
    Args:
        prefix: Optional prefix for the run ID
        
    Returns:
        Run ID string like "2024-03-16_143052" or "prefix_2024-03-16_143052"
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if prefix:
        return f"{prefix}_{timestamp}"
    return timestamp


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable form.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string like "1h 23m 45s" or "45.2s" or "123.4ms"
    """
    if seconds < 0.001:
        return f"{seconds * 1e6:.1f}µs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.0f}s"
