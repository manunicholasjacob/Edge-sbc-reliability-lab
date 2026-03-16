"""
Utilization-based power proxy estimation.

Provides software-based power estimation using CPU utilization,
frequency, and temperature as proxies. This is NOT a replacement
for actual power measurement but provides useful relative comparisons.

Limitations:
- This is an estimation/proxy, not actual power measurement
- Accuracy depends on workload characteristics
- Should be used for relative comparisons, not absolute values
- For accurate power measurement, use external instrumentation
"""

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import psutil


# Raspberry Pi 5 power model parameters (approximate)
# These are rough estimates based on typical Pi 5 behavior
PI5_POWER_MODEL = {
    "idle_watts": 2.5,      # Approximate idle power
    "max_watts": 8.0,       # Approximate max power under load
    "freq_min_mhz": 1500,   # Minimum frequency
    "freq_max_mhz": 2400,   # Maximum frequency
}


@dataclass
class PowerSample:
    """A single power proxy sample."""
    timestamp_ns: int
    timestamp_sec: float
    cpu_percent: float
    frequency_mhz: float
    temperature_c: float
    estimated_watts: float


def estimate_power_from_utilization(
    cpu_percent: float,
    frequency_mhz: float = 2400,
    temperature_c: float = 50,
    model: Dict = None,
) -> float:
    """
    Estimate power consumption from CPU utilization.
    
    This is a simplified linear model:
    power = idle_power + (max_power - idle_power) * utilization_factor * freq_factor
    
    Args:
        cpu_percent: CPU utilization percentage (0-100)
        frequency_mhz: Current CPU frequency in MHz
        temperature_c: Current temperature (not used in basic model)
        model: Power model parameters (uses PI5 defaults if None)
        
    Returns:
        Estimated power in watts
    """
    if model is None:
        model = PI5_POWER_MODEL
    
    idle = model["idle_watts"]
    max_power = model["max_watts"]
    freq_min = model["freq_min_mhz"]
    freq_max = model["freq_max_mhz"]
    
    # Utilization factor (0-1)
    util_factor = min(1.0, max(0.0, cpu_percent / 100.0))
    
    # Frequency factor (0-1, normalized)
    freq_factor = (frequency_mhz - freq_min) / (freq_max - freq_min)
    freq_factor = min(1.0, max(0.0, freq_factor))
    
    # Combined factor (weighted)
    combined_factor = util_factor * (0.7 + 0.3 * freq_factor)
    
    # Estimate power
    estimated = idle + (max_power - idle) * combined_factor
    
    return estimated


class PowerProxy:
    """
    Continuous power proxy estimation during benchmark runs.
    
    Collects CPU utilization, frequency, and temperature samples
    and estimates power consumption using a simple model.
    
    IMPORTANT: This provides proxy estimates, not actual measurements.
    For accurate power data, use external instrumentation.
    """
    
    def __init__(
        self,
        sample_interval_sec: float = 1.0,
        power_model: Dict = None,
    ):
        """
        Initialize power proxy.
        
        Args:
            sample_interval_sec: Interval between samples
            power_model: Custom power model parameters
        """
        self.sample_interval_sec = max(0.1, sample_interval_sec)
        self.power_model = power_model or PI5_POWER_MODEL
        self.samples: List[PowerSample] = []
        self._start_time_ns: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start(self):
        """Start background power proxy logging."""
        if self._running:
            return
        
        self._start_time_ns = time.monotonic_ns()
        self._running = True
        self.samples = []
        
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> List[PowerSample]:
        """Stop logging and return collected samples."""
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
                # Get CPU utilization
                cpu_percent = psutil.cpu_percent(interval=None)
                
                # Get frequency
                freq = psutil.cpu_freq()
                frequency_mhz = freq.current if freq else 2400
                
                # Get temperature
                temperature_c = self._get_temperature()
                
                # Estimate power
                estimated_watts = estimate_power_from_utilization(
                    cpu_percent,
                    frequency_mhz,
                    temperature_c,
                    self.power_model,
                )
                
                elapsed_ns = time.monotonic_ns() - self._start_time_ns
                
                sample = PowerSample(
                    timestamp_ns=elapsed_ns,
                    timestamp_sec=elapsed_ns / 1e9,
                    cpu_percent=cpu_percent,
                    frequency_mhz=frequency_mhz,
                    temperature_c=temperature_c,
                    estimated_watts=estimated_watts,
                )
                
                with self._lock:
                    self.samples.append(sample)
                
            except Exception:
                pass
            
            time.sleep(self.sample_interval_sec)
    
    def _get_temperature(self) -> float:
        """Get CPU temperature."""
        thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
        if thermal_path.exists():
            try:
                return int(thermal_path.read_text().strip()) / 1000.0
            except Exception:
                pass
        return 50.0  # Default fallback
    
    def get_current_samples(self) -> List[PowerSample]:
        """Get a copy of current samples without stopping."""
        with self._lock:
            return list(self.samples)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert samples to DataFrame."""
        with self._lock:
            if not self.samples:
                return pd.DataFrame(columns=[
                    "timestamp_ns", "timestamp_sec", "cpu_percent",
                    "frequency_mhz", "temperature_c", "estimated_watts"
                ])
            
            return pd.DataFrame([
                {
                    "timestamp_ns": s.timestamp_ns,
                    "timestamp_sec": s.timestamp_sec,
                    "cpu_percent": s.cpu_percent,
                    "frequency_mhz": s.frequency_mhz,
                    "temperature_c": s.temperature_c,
                    "estimated_watts": s.estimated_watts,
                }
                for s in self.samples
            ])
    
    def save_csv(self, path: str):
        """Save samples to CSV file."""
        df = self.to_dataframe()
        df.to_csv(path, index=False)
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics of power proxy samples.
        
        Returns:
            Dictionary with power proxy summary
        """
        with self._lock:
            if not self.samples:
                return {
                    "is_proxy": True,
                    "warning": "Power values are estimates, not measurements",
                    "mean_watts": 0.0,
                    "min_watts": 0.0,
                    "max_watts": 0.0,
                    "total_energy_joules": 0.0,
                    "sample_count": 0,
                    "duration_sec": 0.0,
                }
            
            watts = [s.estimated_watts for s in self.samples]
            duration_sec = self.samples[-1].timestamp_sec
            
            # Estimate total energy (simple integration)
            total_energy = sum(watts) * self.sample_interval_sec
            
            return {
                "is_proxy": True,
                "warning": "Power values are estimates, not measurements",
                "mean_watts": sum(watts) / len(watts),
                "min_watts": min(watts),
                "max_watts": max(watts),
                "total_energy_joules": total_energy,
                "sample_count": len(watts),
                "duration_sec": duration_sec,
                "mean_cpu_percent": sum(s.cpu_percent for s in self.samples) / len(self.samples),
            }
