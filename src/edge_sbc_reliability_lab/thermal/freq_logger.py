"""
CPU frequency logging for performance analysis.

Monitors CPU frequency changes during benchmark runs to detect
throttling and frequency scaling behavior.
"""

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class FreqSample:
    """A single frequency sample."""
    timestamp_ns: int  # Monotonic nanoseconds since logger start
    timestamp_sec: float  # Seconds since logger start
    freq_mhz: float  # Frequency in MHz
    cpu: int = 0  # CPU core number


def get_cpu_frequency(cpu: int = 0) -> float:
    """
    Get current CPU frequency in MHz.
    
    Args:
        cpu: CPU core number
        
    Returns:
        Frequency in MHz, or 0.0 if unavailable
    """
    # Method 1: scaling_cur_freq (most common)
    freq_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq")
    if freq_path.exists():
        try:
            freq_khz = int(freq_path.read_text().strip())
            return freq_khz / 1000.0
        except Exception:
            pass
    
    # Method 2: cpuinfo_cur_freq
    freq_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/cpuinfo_cur_freq")
    if freq_path.exists():
        try:
            freq_khz = int(freq_path.read_text().strip())
            return freq_khz / 1000.0
        except Exception:
            pass
    
    # Method 3: psutil
    try:
        import psutil
        freq = psutil.cpu_freq(percpu=True)
        if freq and len(freq) > cpu:
            return freq[cpu].current
    except Exception:
        pass
    
    return 0.0


def get_all_cpu_frequencies() -> Dict[int, float]:
    """
    Get frequencies for all CPU cores.
    
    Returns:
        Dictionary mapping CPU number to frequency in MHz
    """
    frequencies = {}
    cpu_path = Path("/sys/devices/system/cpu")
    
    if not cpu_path.exists():
        return frequencies
    
    for cpu_dir in sorted(cpu_path.glob("cpu[0-9]*")):
        try:
            cpu_num = int(cpu_dir.name.replace("cpu", ""))
            freq = get_cpu_frequency(cpu_num)
            if freq > 0:
                frequencies[cpu_num] = freq
        except (ValueError, Exception):
            continue
    
    return frequencies


def get_frequency_limits(cpu: int = 0) -> Dict[str, float]:
    """
    Get CPU frequency limits.
    
    Args:
        cpu: CPU core number
        
    Returns:
        Dictionary with min, max, and current frequencies in MHz
    """
    base_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq")
    limits = {
        "min_mhz": 0.0,
        "max_mhz": 0.0,
        "current_mhz": 0.0,
    }
    
    freq_files = {
        "min_mhz": "cpuinfo_min_freq",
        "max_mhz": "cpuinfo_max_freq",
        "current_mhz": "scaling_cur_freq",
    }
    
    for key, filename in freq_files.items():
        path = base_path / filename
        if path.exists():
            try:
                freq_khz = int(path.read_text().strip())
                limits[key] = freq_khz / 1000.0
            except Exception:
                pass
    
    return limits


class FreqLogger:
    """
    Continuous CPU frequency logger for benchmark runs.
    
    Runs in a background thread and collects frequency samples
    at a configurable interval.
    """
    
    def __init__(self, sample_interval_sec: float = 1.0, cpu: int = 0):
        """
        Initialize frequency logger.
        
        Args:
            sample_interval_sec: Interval between samples in seconds
            cpu: CPU core to monitor (default 0)
        """
        self.sample_interval_sec = max(0.1, sample_interval_sec)
        self.cpu = cpu
        self.samples: List[FreqSample] = []
        self._start_time_ns: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start background frequency logging."""
        if self._running:
            return
        
        self._start_time_ns = time.monotonic_ns()
        self._running = True
        self.samples = []
        
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> List[FreqSample]:
        """
        Stop logging and return collected samples.
        
        Returns:
            List of frequency samples
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        with self._lock:
            return list(self.samples)
    
    def _logging_loop(self):
        """Background logging loop."""
        while self._running:
            try:
                freq = get_cpu_frequency(self.cpu)
                elapsed_ns = time.monotonic_ns() - self._start_time_ns
                
                sample = FreqSample(
                    timestamp_ns=elapsed_ns,
                    timestamp_sec=elapsed_ns / 1e9,
                    freq_mhz=freq,
                    cpu=self.cpu
                )
                
                with self._lock:
                    self.samples.append(sample)
                
            except Exception:
                pass
            
            time.sleep(self.sample_interval_sec)
    
    def get_current_samples(self) -> List[FreqSample]:
        """Get a copy of current samples without stopping."""
        with self._lock:
            return list(self.samples)
    
    def get_latest_freq(self) -> float:
        """Get the most recent frequency reading."""
        with self._lock:
            if self.samples:
                return self.samples[-1].freq_mhz
        return get_cpu_frequency(self.cpu)
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert samples to DataFrame.
        
        Returns:
            DataFrame with timestamp and frequency columns
        """
        with self._lock:
            if not self.samples:
                return pd.DataFrame(columns=["timestamp_ns", "timestamp_sec", "freq_mhz", "cpu"])
            
            return pd.DataFrame([
                {
                    "timestamp_ns": s.timestamp_ns,
                    "timestamp_sec": s.timestamp_sec,
                    "freq_mhz": s.freq_mhz,
                    "cpu": s.cpu,
                }
                for s in self.samples
            ])
    
    def save_csv(self, path: str):
        """Save samples to CSV file."""
        df = self.to_dataframe()
        df.to_csv(path, index=False)
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of frequency samples.
        
        Returns:
            Dictionary with min, max, mean frequencies and throttle detection
        """
        with self._lock:
            if not self.samples:
                return {
                    "min_mhz": 0.0,
                    "max_mhz": 0.0,
                    "mean_mhz": 0.0,
                    "start_mhz": 0.0,
                    "end_mhz": 0.0,
                    "sample_count": 0,
                    "duration_sec": 0.0,
                    "throttle_detected": False,
                }
            
            freqs = [s.freq_mhz for s in self.samples]
            limits = get_frequency_limits(self.cpu)
            
            # Detect throttling: frequency dropped significantly below max
            max_freq = limits.get("max_mhz", max(freqs))
            throttle_threshold = max_freq * 0.9  # 90% of max
            throttle_detected = min(freqs) < throttle_threshold
            
            return {
                "min_mhz": min(freqs),
                "max_mhz": max(freqs),
                "mean_mhz": sum(freqs) / len(freqs),
                "start_mhz": freqs[0],
                "end_mhz": freqs[-1],
                "sample_count": len(freqs),
                "duration_sec": self.samples[-1].timestamp_sec,
                "throttle_detected": throttle_detected,
                "freq_limit_max_mhz": max_freq,
            }
