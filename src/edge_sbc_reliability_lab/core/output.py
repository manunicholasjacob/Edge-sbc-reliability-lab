"""
Output management for benchmark results.

Handles creation of structured output directories, saving of results,
and generation of manifests for reproducibility.
"""

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import yaml


@dataclass
class RunPaths:
    """Paths for a single benchmark run."""
    run_dir: Path
    manifest_path: Path
    config_path: Path
    system_snapshot_path: Path
    latency_samples_path: Path
    thermal_trace_path: Path
    frequency_trace_path: Path
    power_proxy_path: Path
    summary_path: Path
    warnings_path: Path
    figures_dir: Path
    logs_dir: Path


class OutputManager:
    """
    Manages output directory structure and file writing for benchmark runs.
    
    Creates a standardized directory structure:
    results/
      YYYY-MM-DD_experiment_name_runXXX/
        manifest.json
        config_resolved.yaml
        system_snapshot.json
        latency_samples.csv
        thermal_trace.csv
        frequency_trace.csv
        power_proxy.csv
        summary.json
        warnings.json
        figures/
        logs/
    """
    
    def __init__(self, base_output_dir: Union[str, Path] = "results"):
        """
        Initialize output manager.
        
        Args:
            base_output_dir: Base directory for all results
        """
        self.base_dir = Path(base_output_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_run_directory(
        self,
        experiment_name: str,
        model_name: str = "",
        runtime: str = "",
        run_number: Optional[int] = None
    ) -> RunPaths:
        """
        Create a new run directory with standardized structure.
        
        Args:
            experiment_name: Name of the experiment
            model_name: Optional model name for directory naming
            runtime: Optional runtime name for directory naming
            run_number: Optional run number, auto-incremented if not provided
            
        Returns:
            RunPaths with all output file paths
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Build directory name
        name_parts = [date_str]
        if experiment_name:
            name_parts.append(self._sanitize_name(experiment_name))
        if model_name:
            name_parts.append(self._sanitize_name(model_name))
        if runtime:
            name_parts.append(runtime)
        
        base_name = "_".join(name_parts)
        
        # Find next run number if not specified
        if run_number is None:
            run_number = self._get_next_run_number(base_name)
        
        run_name = f"{base_name}_run{run_number:03d}"
        run_dir = self.base_dir / run_name
        
        # Create directory structure
        run_dir.mkdir(parents=True, exist_ok=True)
        figures_dir = run_dir / "figures"
        figures_dir.mkdir(exist_ok=True)
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        return RunPaths(
            run_dir=run_dir,
            manifest_path=run_dir / "manifest.json",
            config_path=run_dir / "config_resolved.yaml",
            system_snapshot_path=run_dir / "system_snapshot.json",
            latency_samples_path=run_dir / "latency_samples.csv",
            thermal_trace_path=run_dir / "thermal_trace.csv",
            frequency_trace_path=run_dir / "frequency_trace.csv",
            power_proxy_path=run_dir / "power_proxy.csv",
            summary_path=run_dir / "summary.json",
            warnings_path=run_dir / "warnings.json",
            figures_dir=figures_dir,
            logs_dir=logs_dir,
        )
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize name for use in file paths."""
        # Replace spaces and special chars with underscores
        sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        # Remove consecutive underscores
        while "__" in sanitized:
            sanitized = sanitized.replace("__", "_")
        return sanitized.strip("_").lower()
    
    def _get_next_run_number(self, base_name: str) -> int:
        """Find the next available run number for a base name."""
        existing = list(self.base_dir.glob(f"{base_name}_run*"))
        if not existing:
            return 1
        
        max_num = 0
        for path in existing:
            try:
                # Extract run number from directory name
                num_str = path.name.split("_run")[-1]
                num = int(num_str)
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue
        
        return max_num + 1
    
    @staticmethod
    def save_json(data: Dict[str, Any], path: Union[str, Path], indent: int = 2):
        """Save dictionary as JSON file."""
        path = Path(path)
        with open(path, "w") as f:
            json.dump(data, f, indent=indent, default=str)
    
    @staticmethod
    def save_yaml(data: Dict[str, Any], path: Union[str, Path]):
        """Save dictionary as YAML file."""
        path = Path(path)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    @staticmethod
    def save_csv(df: pd.DataFrame, path: Union[str, Path], index: bool = False):
        """Save DataFrame as CSV file."""
        path = Path(path)
        df.to_csv(path, index=index)
    
    @staticmethod
    def save_latency_samples(
        latencies_ns: List[int],
        timestamps_ns: List[int],
        path: Union[str, Path]
    ):
        """
        Save latency samples with timestamps.
        
        Args:
            latencies_ns: List of latency measurements in nanoseconds
            timestamps_ns: List of timestamps (elapsed ns from start)
            path: Output CSV path
        """
        df = pd.DataFrame({
            "sample_index": range(len(latencies_ns)),
            "timestamp_ns": timestamps_ns,
            "timestamp_sec": [t / 1e9 for t in timestamps_ns],
            "latency_ns": latencies_ns,
            "latency_ms": [l / 1e6 for l in latencies_ns],
        })
        df.to_csv(path, index=False)
    
    @staticmethod
    def load_json(path: Union[str, Path]) -> Dict[str, Any]:
        """Load JSON file as dictionary."""
        with open(path, "r") as f:
            return json.load(f)
    
    @staticmethod
    def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
        """Load YAML file as dictionary."""
        with open(path, "r") as f:
            return yaml.safe_load(f)
    
    def list_runs(self, pattern: str = "*") -> List[Path]:
        """
        List all run directories matching a pattern.
        
        Args:
            pattern: Glob pattern to filter runs
            
        Returns:
            List of run directory paths, sorted by name
        """
        runs = [p for p in self.base_dir.glob(pattern) if p.is_dir()]
        return sorted(runs)
    
    def get_latest_run(self, pattern: str = "*") -> Optional[Path]:
        """
        Get the most recent run directory.
        
        Args:
            pattern: Glob pattern to filter runs
            
        Returns:
            Path to latest run directory, or None if no runs exist
        """
        runs = self.list_runs(pattern)
        return runs[-1] if runs else None


def create_manifest(
    config: Dict[str, Any],
    system_snapshot: Dict[str, Any],
    summary: Dict[str, Any],
    warnings: List[str],
    run_paths: RunPaths,
    start_time: str,
    end_time: str,
    duration_sec: float,
) -> Dict[str, Any]:
    """
    Create a manifest documenting the benchmark run.
    
    Args:
        config: Resolved experiment configuration
        system_snapshot: System environment snapshot
        summary: Benchmark results summary
        warnings: List of warning messages
        run_paths: Paths to all output files
        start_time: ISO format start time
        end_time: ISO format end time
        duration_sec: Total run duration in seconds
        
    Returns:
        Manifest dictionary
    """
    return {
        "manifest_version": "1.0",
        "framework": "edge-sbc-reliability-lab",
        "framework_version": "1.0.0",
        "run_id": run_paths.run_dir.name,
        "experiment_name": config.get("experiment_name", "unknown"),
        "start_time": start_time,
        "end_time": end_time,
        "duration_sec": duration_sec,
        "config_hash": config.get("config_hash", ""),
        "files": {
            "config": run_paths.config_path.name,
            "system_snapshot": run_paths.system_snapshot_path.name,
            "latency_samples": run_paths.latency_samples_path.name,
            "thermal_trace": run_paths.thermal_trace_path.name,
            "frequency_trace": run_paths.frequency_trace_path.name,
            "power_proxy": run_paths.power_proxy_path.name,
            "summary": run_paths.summary_path.name,
            "warnings": run_paths.warnings_path.name,
        },
        "platform": {
            "device": system_snapshot.get("device_model", "unknown"),
            "os": system_snapshot.get("os_version", "unknown"),
            "python": system_snapshot.get("python_version", "unknown"),
        },
        "benchmark": {
            "runtime": config.get("runtime", "unknown"),
            "model": config.get("model_name", "unknown"),
            "total_inferences": summary.get("total_inferences", 0),
        },
        "warnings_count": len(warnings),
        "success": summary.get("success", False),
    }
