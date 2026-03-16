"""
CPU governor checking and validation.

Provides utilities to check CPU frequency governor state for fair benchmarking.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_cpu_governor(cpu: int = 0) -> str:
    """
    Get the CPU frequency governor for a specific CPU.
    
    Args:
        cpu: CPU number (default 0)
        
    Returns:
        Governor name (e.g., "performance", "ondemand", "schedutil")
    """
    governor_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
    if governor_path.exists():
        try:
            return governor_path.read_text().strip()
        except Exception:
            pass
    return "unknown"


def get_all_cpu_governors() -> Dict[int, str]:
    """
    Get governors for all CPUs.
    
    Returns:
        Dictionary mapping CPU number to governor name
    """
    governors = {}
    cpu_path = Path("/sys/devices/system/cpu")
    
    if not cpu_path.exists():
        return governors
    
    for cpu_dir in sorted(cpu_path.glob("cpu[0-9]*")):
        try:
            cpu_num = int(cpu_dir.name.replace("cpu", ""))
            governor_path = cpu_dir / "cpufreq" / "scaling_governor"
            if governor_path.exists():
                governors[cpu_num] = governor_path.read_text().strip()
        except (ValueError, Exception):
            continue
    
    return governors


def check_governor_consistency() -> Tuple[bool, str, Dict[int, str]]:
    """
    Check if all CPUs have the same governor.
    
    Returns:
        Tuple of (is_consistent, governor_name, all_governors)
    """
    governors = get_all_cpu_governors()
    
    if not governors:
        return True, "unknown", {}
    
    unique_governors = set(governors.values())
    
    if len(unique_governors) == 1:
        return True, list(unique_governors)[0], governors
    else:
        return False, "mixed", governors


def get_available_governors(cpu: int = 0) -> List[str]:
    """
    Get list of available governors for a CPU.
    
    Args:
        cpu: CPU number
        
    Returns:
        List of available governor names
    """
    path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_available_governors")
    if path.exists():
        try:
            return path.read_text().strip().split()
        except Exception:
            pass
    return []


def is_performance_governor() -> bool:
    """Check if CPU is using performance governor."""
    return get_cpu_governor() == "performance"


def get_governor_recommendation() -> str:
    """
    Get recommendation for governor setting for benchmarking.
    
    Returns:
        Recommendation string
    """
    current = get_cpu_governor()
    available = get_available_governors()
    
    if current == "performance":
        return "Governor is set to 'performance' - optimal for benchmarking."
    elif "performance" in available:
        return (
            f"Governor is '{current}'. For consistent benchmarks, consider:\n"
            f"  sudo cpufreq-set -g performance\n"
            f"  or: echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
        )
    else:
        return (
            f"Governor is '{current}'. 'performance' governor not available.\n"
            f"Available governors: {', '.join(available)}"
        )


def get_cpu_frequency_info(cpu: int = 0) -> Dict[str, float]:
    """
    Get CPU frequency information.
    
    Args:
        cpu: CPU number
        
    Returns:
        Dictionary with current, min, and max frequencies in MHz
    """
    base_path = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq")
    info = {
        "current_mhz": 0.0,
        "min_mhz": 0.0,
        "max_mhz": 0.0,
    }
    
    freq_files = {
        "current_mhz": "scaling_cur_freq",
        "min_mhz": "cpuinfo_min_freq",
        "max_mhz": "cpuinfo_max_freq",
    }
    
    for key, filename in freq_files.items():
        path = base_path / filename
        if path.exists():
            try:
                # Frequency is in kHz in sysfs
                freq_khz = int(path.read_text().strip())
                info[key] = freq_khz / 1000.0
            except Exception:
                pass
    
    return info
