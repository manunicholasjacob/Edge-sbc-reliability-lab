"""
Temperature logging for thermal behavior analysis.

Provides continuous temperature monitoring during benchmark runs.
"""

import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


@dataclass
class TempSample:
    """A single temperature sample."""
    timestamp_ns: int  # Monotonic nanoseconds since logger start
    timestamp_sec: float  # Seconds since logger start
    temp_c: float  # Temperature in Celsius


def get_cpu_temperature() -> float:
    """
    Get current CPU temperature in Celsius.
    
    Tries multiple methods in order of preference for Raspberry Pi.
    
    Returns:
        Temperature in Celsius, or 0.0 if unavailable
    """
    # Method 1: thermal_zone0 (most reliable on Pi)
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.exists():
        try:
            temp_millic = int(thermal_path.read_text().strip())
            return temp_millic / 1000.0
        except Exception:
            pass
    
    # Method 2: vcgencmd (Raspberry Pi specific)
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # Parse "temp=45.0'C"
            temp_str = result.stdout.strip()
            temp_val = temp_str.replace("temp=", "").replace("'C", "")
            return float(temp_val)
    except Exception:
        pass
    
    # Method 3: psutil sensors
    try:
        import psutil
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
    except Exception:
        pass
    
    return 0.0


class TempLogger:
    """
    Continuous temperature logger for benchmark runs.
    
    Runs in a background thread and collects temperature samples
    at a configurable interval.
    """
    
    def __init__(self, sample_interval_sec: float = 1.0):
        """
        Initialize temperature logger.
        
        Args:
            sample_interval_sec: Interval between samples in seconds
        """
        self.sample_interval_sec = max(0.1, sample_interval_sec)
        self.samples: List[TempSample] = []
        self._start_time_ns: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start background temperature logging."""
        if self._running:
            return
        
        self._start_time_ns = time.monotonic_ns()
        self._running = True
        self.samples = []
        
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> List[TempSample]:
        """
        Stop logging and return collected samples.
        
        Returns:
            List of temperature samples
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
                temp = get_cpu_temperature()
                elapsed_ns = time.monotonic_ns() - self._start_time_ns
                
                sample = TempSample(
                    timestamp_ns=elapsed_ns,
                    timestamp_sec=elapsed_ns / 1e9,
                    temp_c=temp
                )
                
                with self._lock:
                    self.samples.append(sample)
                
            except Exception:
                pass
            
            time.sleep(self.sample_interval_sec)
    
    def get_current_samples(self) -> List[TempSample]:
        """Get a copy of current samples without stopping."""
        with self._lock:
            return list(self.samples)
    
    def get_latest_temp(self) -> float:
        """Get the most recent temperature reading."""
        with self._lock:
            if self.samples:
                return self.samples[-1].temp_c
        return get_cpu_temperature()
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert samples to DataFrame.
        
        Returns:
            DataFrame with timestamp and temperature columns
        """
        with self._lock:
            if not self.samples:
                return pd.DataFrame(columns=["timestamp_ns", "timestamp_sec", "temp_c"])
            
            return pd.DataFrame([
                {
                    "timestamp_ns": s.timestamp_ns,
                    "timestamp_sec": s.timestamp_sec,
                    "temp_c": s.temp_c,
                }
                for s in self.samples
            ])
    
    def save_csv(self, path: str):
        """Save samples to CSV file."""
        df = self.to_dataframe()
        df.to_csv(path, index=False)
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of temperature samples.
        
        Returns:
            Dictionary with min, max, mean, start, end temperatures
        """
        with self._lock:
            if not self.samples:
                return {
                    "min_c": 0.0,
                    "max_c": 0.0,
                    "mean_c": 0.0,
                    "start_c": 0.0,
                    "end_c": 0.0,
                    "range_c": 0.0,
                    "sample_count": 0,
                    "duration_sec": 0.0,
                }
            
            temps = [s.temp_c for s in self.samples]
            
            return {
                "min_c": min(temps),
                "max_c": max(temps),
                "mean_c": sum(temps) / len(temps),
                "start_c": temps[0],
                "end_c": temps[-1],
                "range_c": max(temps) - min(temps),
                "sample_count": len(temps),
                "duration_sec": self.samples[-1].timestamp_sec,
            }


def wait_for_cooldown(
    target_temp_c: float,
    timeout_sec: float = 300,
    check_interval_sec: float = 5.0,
    callback=None
) -> Tuple[bool, float]:
    """
    Wait for CPU to cool down to target temperature.
    
    Args:
        target_temp_c: Target temperature in Celsius
        timeout_sec: Maximum wait time in seconds
        check_interval_sec: Interval between temperature checks
        callback: Optional callback(current_temp, elapsed_sec) for progress
        
    Returns:
        Tuple of (success, final_temperature)
    """
    start_time = time.time()
    
    while True:
        current_temp = get_cpu_temperature()
        elapsed = time.time() - start_time
        
        if callback:
            callback(current_temp, elapsed)
        
        if current_temp <= target_temp_c:
            return True, current_temp
        
        if elapsed >= timeout_sec:
            return False, current_temp
        
        time.sleep(check_interval_sec)
