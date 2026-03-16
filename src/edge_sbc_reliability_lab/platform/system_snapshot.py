"""
System snapshot capture for reproducibility.

Captures comprehensive system state including hardware, OS, packages,
and runtime environment for Raspberry Pi 5 benchmarking.
"""

import hashlib
import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil


@dataclass
class SystemSnapshot:
    """Complete system state snapshot."""
    
    # Identification
    snapshot_time: str = ""
    hostname: str = ""
    
    # Hardware
    device_model: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    
    # OS and kernel
    os_name: str = ""
    os_version: str = ""
    kernel_version: str = ""
    architecture: str = ""
    
    # Python environment
    python_version: str = ""
    python_executable: str = ""
    
    # Package versions
    package_versions: Dict[str, str] = field(default_factory=dict)
    
    # CPU state
    cpu_governor: str = ""
    cpu_freq_current_mhz: float = 0.0
    cpu_freq_min_mhz: float = 0.0
    cpu_freq_max_mhz: float = 0.0
    
    # Thermal state
    cpu_temp_c: float = 0.0
    
    # Git info (if in repo)
    git_commit: str = ""
    git_branch: str = ""
    git_dirty: bool = False
    
    # Experiment metadata
    config_hash: str = ""
    cooling_note: str = ""
    ambient_note: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "snapshot_time": self.snapshot_time,
            "hostname": self.hostname,
            "device_model": self.device_model,
            "cpu_model": self.cpu_model,
            "cpu_cores": self.cpu_cores,
            "cpu_threads": self.cpu_threads,
            "ram_total_gb": self.ram_total_gb,
            "ram_available_gb": self.ram_available_gb,
            "os_name": self.os_name,
            "os_version": self.os_version,
            "kernel_version": self.kernel_version,
            "architecture": self.architecture,
            "python_version": self.python_version,
            "python_executable": self.python_executable,
            "package_versions": self.package_versions,
            "cpu_governor": self.cpu_governor,
            "cpu_freq_current_mhz": self.cpu_freq_current_mhz,
            "cpu_freq_min_mhz": self.cpu_freq_min_mhz,
            "cpu_freq_max_mhz": self.cpu_freq_max_mhz,
            "cpu_temp_c": self.cpu_temp_c,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "config_hash": self.config_hash,
            "cooling_note": self.cooling_note,
            "ambient_note": self.ambient_note,
        }


def capture_system_snapshot(
    config_hash: str = "",
    cooling_note: str = "",
    ambient_note: str = "",
) -> SystemSnapshot:
    """
    Capture comprehensive system snapshot.
    
    Args:
        config_hash: Hash of experiment configuration
        cooling_note: Note about cooling setup
        ambient_note: Note about ambient conditions
        
    Returns:
        SystemSnapshot with all captured information
    """
    snapshot = SystemSnapshot()
    
    # Timestamp
    snapshot.snapshot_time = datetime.now(timezone.utc).isoformat()
    snapshot.hostname = socket.gethostname()
    
    # Hardware info
    snapshot.device_model = _get_device_model()
    snapshot.cpu_model = _get_cpu_model()
    snapshot.cpu_cores = psutil.cpu_count(logical=False) or 0
    snapshot.cpu_threads = psutil.cpu_count(logical=True) or 0
    
    # Memory
    mem = psutil.virtual_memory()
    snapshot.ram_total_gb = round(mem.total / (1024**3), 2)
    snapshot.ram_available_gb = round(mem.available / (1024**3), 2)
    
    # OS info
    snapshot.os_name = platform.system()
    snapshot.os_version = _get_os_version()
    snapshot.kernel_version = platform.release()
    snapshot.architecture = platform.machine()
    
    # Python
    snapshot.python_version = platform.python_version()
    snapshot.python_executable = sys.executable
    
    # Package versions
    snapshot.package_versions = _get_package_versions()
    
    # CPU state
    snapshot.cpu_governor = _get_cpu_governor()
    freq = psutil.cpu_freq()
    if freq:
        snapshot.cpu_freq_current_mhz = freq.current
        snapshot.cpu_freq_min_mhz = freq.min
        snapshot.cpu_freq_max_mhz = freq.max
    
    # Temperature
    snapshot.cpu_temp_c = _get_cpu_temperature()
    
    # Git info
    git_info = _get_git_info()
    snapshot.git_commit = git_info.get("commit", "")
    snapshot.git_branch = git_info.get("branch", "")
    snapshot.git_dirty = git_info.get("dirty", False)
    
    # Experiment metadata
    snapshot.config_hash = config_hash
    snapshot.cooling_note = cooling_note
    snapshot.ambient_note = ambient_note
    
    return snapshot


def _get_device_model() -> str:
    """Get device model string."""
    # Try Raspberry Pi model file
    model_path = Path("/proc/device-tree/model")
    if model_path.exists():
        try:
            return model_path.read_text().strip().rstrip('\x00')
        except Exception:
            pass
    
    # Try DMI info
    dmi_path = Path("/sys/class/dmi/id/product_name")
    if dmi_path.exists():
        try:
            return dmi_path.read_text().strip()
        except Exception:
            pass
    
    return platform.node()


def _get_cpu_model() -> str:
    """Get CPU model string."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("model name") or line.startswith("Model"):
                    return line.split(":")[-1].strip()
    except Exception:
        pass
    
    return platform.processor() or "unknown"


def _get_os_version() -> str:
    """Get OS version string."""
    try:
        # Try /etc/os-release first
        os_release = Path("/etc/os-release")
        if os_release.exists():
            content = os_release.read_text()
            for line in content.split("\n"):
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    
    return f"{platform.system()} {platform.release()}"


def _get_cpu_governor() -> str:
    """Get current CPU frequency governor."""
    governor_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if governor_path.exists():
        try:
            return governor_path.read_text().strip()
        except Exception:
            pass
    return "unknown"


def _get_cpu_temperature() -> float:
    """Get current CPU temperature in Celsius."""
    # Try thermal zone (works on Pi)
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.exists():
        try:
            temp_millic = int(thermal_path.read_text().strip())
            return temp_millic / 1000.0
        except Exception:
            pass
    
    # Try vcgencmd (Raspberry Pi specific)
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse "temp=45.0'C"
            temp_str = result.stdout.strip()
            temp_val = temp_str.replace("temp=", "").replace("'C", "")
            return float(temp_val)
    except Exception:
        pass
    
    # Try psutil sensors
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    return entries[0].current
    except Exception:
        pass
    
    return 0.0


def _get_package_versions() -> Dict[str, str]:
    """Get versions of relevant packages."""
    packages = [
        "numpy",
        "pandas",
        "onnxruntime",
        "tflite-runtime",
        "torch",
        "psutil",
        "pyyaml",
        "matplotlib",
    ]
    
    versions = {}
    
    try:
        import importlib.metadata as metadata
    except ImportError:
        import importlib_metadata as metadata
    
    for pkg in packages:
        try:
            versions[pkg] = metadata.version(pkg)
        except Exception:
            # Try alternative names
            alt_names = {
                "tflite-runtime": "tflite_runtime",
                "pyyaml": "PyYAML",
            }
            if pkg in alt_names:
                try:
                    versions[pkg] = metadata.version(alt_names[pkg])
                except Exception:
                    pass
    
    return versions


def _get_git_info() -> Dict[str, Any]:
    """Get git repository information if available."""
    info = {"commit": "", "branch": "", "dirty": False}
    
    try:
        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["commit"] = result.stdout.strip()[:12]
        
        # Get branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["branch"] = result.stdout.strip()
        
        # Check if dirty
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info["dirty"] = bool(result.stdout.strip())
    except Exception:
        pass
    
    return info
