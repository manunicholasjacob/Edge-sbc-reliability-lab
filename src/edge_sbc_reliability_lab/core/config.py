"""
Experiment configuration loading and validation.

Provides YAML-based configuration with sensible defaults for Raspberry Pi 5 benchmarking.
"""

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class ExperimentConfig:
    """Configuration for a benchmark experiment."""
    
    # Experiment identification
    experiment_name: str = "benchmark"
    description: str = ""
    
    # Model configuration
    model_name: str = "model"
    model_path: str = ""
    runtime: str = "onnx"  # onnx, tflite, torch
    input_shape: List[int] = field(default_factory=lambda: [1, 3, 224, 224])
    input_dtype: str = "float32"
    
    # Benchmark parameters
    batch_size: int = 1
    warmup_runs: int = 10
    measured_runs: int = 100
    sustained_duration_sec: float = 0.0  # 0 = use measured_runs instead
    threads: int = 4
    cpu_affinity: Optional[List[int]] = None
    repeat_count: int = 1
    
    # Telemetry collection
    collect_temperature: bool = True
    collect_frequency: bool = True
    collect_power_proxy: bool = True
    thermal_sample_interval_sec: float = 1.0
    
    # External power measurement
    external_power_trace_path: Optional[str] = None
    
    # Environment notes
    cooling_setup_note: str = "default"
    ambient_note: str = "room temperature"
    
    # Output configuration
    output_dir: str = "results"
    save_raw_latencies: bool = True
    save_thermal_trace: bool = True
    generate_plots: bool = True
    
    # Advanced options
    inter_inference_delay_ms: float = 0.0
    pre_run_cooldown_sec: float = 0.0
    target_start_temp_c: Optional[float] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        valid_runtimes = ["onnx", "tflite", "torch"]
        if self.runtime not in valid_runtimes:
            raise ValueError(f"runtime must be one of {valid_runtimes}, got '{self.runtime}'")
        
        if self.batch_size < 1:
            raise ValueError(f"batch_size must be >= 1, got {self.batch_size}")
        
        if self.warmup_runs < 0:
            raise ValueError(f"warmup_runs must be >= 0, got {self.warmup_runs}")
        
        if self.measured_runs < 1 and self.sustained_duration_sec <= 0:
            raise ValueError("Either measured_runs >= 1 or sustained_duration_sec > 0 required")
        
        if self.threads < 1:
            raise ValueError(f"threads must be >= 1, got {self.threads}")
        
        if self.thermal_sample_interval_sec < 0.1:
            raise ValueError(f"thermal_sample_interval_sec must be >= 0.1, got {self.thermal_sample_interval_sec}")
        
        valid_dtypes = ["float32", "float16", "int8", "uint8"]
        if self.input_dtype not in valid_dtypes:
            raise ValueError(f"input_dtype must be one of {valid_dtypes}, got '{self.input_dtype}'")
    
    def get_config_hash(self) -> str:
        """Generate a hash of the configuration for reproducibility tracking."""
        config_str = yaml.dump(self.to_dict(), sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "experiment_name": self.experiment_name,
            "description": self.description,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "runtime": self.runtime,
            "input_shape": self.input_shape,
            "input_dtype": self.input_dtype,
            "batch_size": self.batch_size,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
            "sustained_duration_sec": self.sustained_duration_sec,
            "threads": self.threads,
            "cpu_affinity": self.cpu_affinity,
            "repeat_count": self.repeat_count,
            "collect_temperature": self.collect_temperature,
            "collect_frequency": self.collect_frequency,
            "collect_power_proxy": self.collect_power_proxy,
            "thermal_sample_interval_sec": self.thermal_sample_interval_sec,
            "external_power_trace_path": self.external_power_trace_path,
            "cooling_setup_note": self.cooling_setup_note,
            "ambient_note": self.ambient_note,
            "output_dir": self.output_dir,
            "save_raw_latencies": self.save_raw_latencies,
            "save_thermal_trace": self.save_thermal_trace,
            "generate_plots": self.generate_plots,
            "inter_inference_delay_ms": self.inter_inference_delay_ms,
            "pre_run_cooldown_sec": self.pre_run_cooldown_sec,
            "target_start_temp_c": self.target_start_temp_c,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """Create configuration from dictionary."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def save(self, path: Union[str, Path]):
        """Save configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)


def load_config(path: Union[str, Path]) -> ExperimentConfig:
    """
    Load experiment configuration from YAML file.
    
    Args:
        path: Path to YAML configuration file
        
    Returns:
        ExperimentConfig instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    
    if data is None:
        data = {}
    
    return ExperimentConfig.from_dict(data)


def get_default_config() -> ExperimentConfig:
    """Get default configuration for Raspberry Pi 5."""
    return ExperimentConfig(
        experiment_name="pi5_default",
        description="Default Raspberry Pi 5 benchmark configuration",
        runtime="onnx",
        input_shape=[1, 3, 224, 224],
        batch_size=1,
        warmup_runs=10,
        measured_runs=100,
        threads=4,
        collect_temperature=True,
        collect_frequency=True,
        collect_power_proxy=True,
    )
