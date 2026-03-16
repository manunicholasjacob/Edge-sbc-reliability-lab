"""
Environment capture utilities for reproducibility.

Captures runtime environment details for experiment documentation.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def capture_environment_variables(
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Capture relevant environment variables.
    
    Args:
        include_patterns: Patterns to include (if None, uses defaults)
        exclude_patterns: Patterns to exclude
        
    Returns:
        Dictionary of environment variables
    """
    if include_patterns is None:
        include_patterns = [
            "PATH",
            "PYTHONPATH",
            "VIRTUAL_ENV",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "ONNX",
            "TF_",
            "CUDA",
            "LD_LIBRARY_PATH",
        ]
    
    if exclude_patterns is None:
        exclude_patterns = ["SECRET", "KEY", "TOKEN", "PASSWORD", "CREDENTIAL"]
    
    env_vars = {}
    
    for key, value in os.environ.items():
        # Check exclusions first
        if any(pattern.lower() in key.lower() for pattern in exclude_patterns):
            continue
        
        # Check inclusions
        if any(pattern.lower() in key.lower() for pattern in include_patterns):
            env_vars[key] = value
    
    return env_vars


def capture_disk_info(path: str = ".") -> Dict[str, Any]:
    """
    Capture disk space information.
    
    Args:
        path: Path to check disk space for
        
    Returns:
        Dictionary with disk information
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        return {
            "path": str(Path(path).resolve()),
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "used_percent": round(used / total * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def capture_process_info() -> Dict[str, Any]:
    """
    Capture current process information.
    
    Returns:
        Dictionary with process information
    """
    import psutil
    
    try:
        process = psutil.Process()
        return {
            "pid": process.pid,
            "name": process.name(),
            "cpu_affinity": list(process.cpu_affinity()) if hasattr(process, "cpu_affinity") else [],
            "nice": process.nice(),
            "memory_mb": round(process.memory_info().rss / (1024**2), 2),
            "num_threads": process.num_threads(),
            "create_time": process.create_time(),
        }
    except Exception as e:
        return {"error": str(e)}


def capture_system_load() -> Dict[str, Any]:
    """
    Capture current system load.
    
    Returns:
        Dictionary with load information
    """
    import psutil
    
    try:
        load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
        return {
            "load_1min": load_avg[0],
            "load_5min": load_avg[1],
            "load_15min": load_avg[2],
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
        }
    except Exception as e:
        return {"error": str(e)}


def capture_running_processes(top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Capture top CPU-consuming processes.
    
    Args:
        top_n: Number of top processes to capture
        
    Returns:
        List of process information dictionaries
    """
    import psutil
    
    processes = []
    try:
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0,
                    "memory_percent": info["memory_percent"] or 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return processes[:top_n]
    except Exception:
        return []


def check_background_interference() -> Dict[str, Any]:
    """
    Check for potential background interference with benchmarks.
    
    Returns:
        Dictionary with interference assessment
    """
    import psutil
    
    result = {
        "high_cpu_processes": [],
        "total_cpu_percent": 0,
        "interference_risk": "low",
        "warnings": [],
    }
    
    try:
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.5)
        result["total_cpu_percent"] = cpu_percent
        
        # Check for high CPU processes
        for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
            try:
                if proc.info["cpu_percent"] and proc.info["cpu_percent"] > 10:
                    result["high_cpu_processes"].append({
                        "name": proc.info["name"],
                        "cpu_percent": proc.info["cpu_percent"],
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Assess risk
        if cpu_percent > 50:
            result["interference_risk"] = "high"
            result["warnings"].append(f"High CPU usage: {cpu_percent}%")
        elif cpu_percent > 20:
            result["interference_risk"] = "medium"
            result["warnings"].append(f"Moderate CPU usage: {cpu_percent}%")
        
        # Check memory pressure
        mem = psutil.virtual_memory()
        if mem.percent > 80:
            result["interference_risk"] = "high"
            result["warnings"].append(f"High memory usage: {mem.percent}%")
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def capture_full_environment() -> Dict[str, Any]:
    """
    Capture complete environment information.
    
    Returns:
        Dictionary with all environment information
    """
    return {
        "environment_variables": capture_environment_variables(),
        "disk_info": capture_disk_info(),
        "process_info": capture_process_info(),
        "system_load": capture_system_load(),
        "background_interference": check_background_interference(),
    }
