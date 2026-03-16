"""
Environment validation for reproducibility.

Validates that the execution environment meets requirements
for reproducible benchmark results.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil


def validate_environment(
    required_runtimes: Optional[List[str]] = None,
    min_memory_gb: float = 2.0,
    min_disk_gb: float = 1.0,
) -> Dict[str, Any]:
    """
    Validate execution environment for benchmarking.
    
    Args:
        required_runtimes: List of required inference runtimes
        min_memory_gb: Minimum required memory in GB
        min_disk_gb: Minimum required disk space in GB
        
    Returns:
        Dictionary with validation results
    """
    if required_runtimes is None:
        required_runtimes = ["onnx"]
    
    checks = []
    warnings = []
    errors = []
    
    # Check Python version
    py_version = sys.version_info
    py_check = {
        "name": "Python Version",
        "value": f"{py_version.major}.{py_version.minor}.{py_version.micro}",
        "passed": py_version >= (3, 9),
        "required": ">=3.9",
    }
    checks.append(py_check)
    if not py_check["passed"]:
        errors.append(f"Python {py_check['required']} required, found {py_check['value']}")
    
    # Check available memory
    mem = psutil.virtual_memory()
    mem_gb = mem.total / (1024**3)
    mem_check = {
        "name": "Total Memory",
        "value": f"{mem_gb:.1f} GB",
        "passed": mem_gb >= min_memory_gb,
        "required": f">={min_memory_gb} GB",
    }
    checks.append(mem_check)
    if not mem_check["passed"]:
        warnings.append(f"Low memory: {mem_gb:.1f} GB (recommended: {min_memory_gb} GB)")
    
    # Check disk space
    disk = psutil.disk_usage(".")
    disk_gb = disk.free / (1024**3)
    disk_check = {
        "name": "Free Disk Space",
        "value": f"{disk_gb:.1f} GB",
        "passed": disk_gb >= min_disk_gb,
        "required": f">={min_disk_gb} GB",
    }
    checks.append(disk_check)
    if not disk_check["passed"]:
        errors.append(f"Insufficient disk space: {disk_gb:.1f} GB (required: {min_disk_gb} GB)")
    
    # Check required packages
    required_packages = ["numpy", "pandas", "pyyaml", "psutil"]
    for pkg in required_packages:
        try:
            __import__(pkg)
            pkg_check = {
                "name": f"Package: {pkg}",
                "value": "installed",
                "passed": True,
            }
        except ImportError:
            pkg_check = {
                "name": f"Package: {pkg}",
                "value": "missing",
                "passed": False,
            }
            errors.append(f"Required package not installed: {pkg}")
        checks.append(pkg_check)
    
    # Check inference runtimes
    from edge_sbc_reliability_lab.inference.runtime_interface import check_runtime_available
    
    for runtime in required_runtimes:
        available, version = check_runtime_available(runtime)
        rt_check = {
            "name": f"Runtime: {runtime}",
            "value": version if available else "not installed",
            "passed": available,
        }
        checks.append(rt_check)
        if not available:
            errors.append(f"Required runtime not available: {runtime}")
    
    # Check platform
    is_linux = sys.platform.startswith("linux")
    platform_check = {
        "name": "Platform",
        "value": sys.platform,
        "passed": is_linux,
        "note": "Linux recommended for accurate benchmarks",
    }
    checks.append(platform_check)
    if not is_linux:
        warnings.append("Non-Linux platform - some features may not work correctly")
    
    # Check thermal interface
    thermal_available = Path("/sys/class/thermal/thermal_zone0/temp").exists()
    thermal_check = {
        "name": "Thermal Interface",
        "value": "available" if thermal_available else "unavailable",
        "passed": thermal_available,
    }
    checks.append(thermal_check)
    if not thermal_available:
        warnings.append("Thermal monitoring unavailable - temperature logging disabled")
    
    # Determine overall status
    all_passed = all(c["passed"] for c in checks)
    has_errors = len(errors) > 0
    
    if has_errors:
        status = "fail"
    elif all_passed:
        status = "pass"
    else:
        status = "warning"
    
    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for c in checks if c["passed"]),
            "failed": sum(1 for c in checks if not c["passed"]),
        }
    }


def check_reproducibility_requirements(
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check requirements for reproducible benchmarking.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Dictionary with reproducibility assessment
    """
    requirements = []
    recommendations = []
    
    # Check CPU governor
    gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov_path.exists():
        governor = gov_path.read_text().strip()
        req = {
            "name": "CPU Governor",
            "current": governor,
            "recommended": "performance",
            "met": governor == "performance",
        }
        requirements.append(req)
        if not req["met"]:
            recommendations.append(
                f"Set CPU governor to 'performance': sudo cpufreq-set -g performance"
            )
    
    # Check temperature
    temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if temp_path.exists():
        try:
            temp = int(temp_path.read_text().strip()) / 1000.0
            req = {
                "name": "Starting Temperature",
                "current": f"{temp:.1f}°C",
                "recommended": "<50°C",
                "met": temp < 50,
            }
            requirements.append(req)
            if not req["met"]:
                recommendations.append(
                    f"Wait for CPU to cool down (current: {temp:.1f}°C)"
                )
        except Exception:
            pass
    
    # Check background load
    cpu_percent = psutil.cpu_percent(interval=0.5)
    req = {
        "name": "Background CPU Load",
        "current": f"{cpu_percent:.0f}%",
        "recommended": "<10%",
        "met": cpu_percent < 10,
    }
    requirements.append(req)
    if not req["met"]:
        recommendations.append(
            f"Close background applications (current CPU: {cpu_percent:.0f}%)"
        )
    
    # Check memory pressure
    mem = psutil.virtual_memory()
    req = {
        "name": "Memory Usage",
        "current": f"{mem.percent:.0f}%",
        "recommended": "<50%",
        "met": mem.percent < 50,
    }
    requirements.append(req)
    if not req["met"]:
        recommendations.append(
            f"Free up memory (current usage: {mem.percent:.0f}%)"
        )
    
    # Determine readiness
    all_met = all(r["met"] for r in requirements)
    
    return {
        "ready": all_met,
        "requirements": requirements,
        "recommendations": recommendations,
        "message": "Environment ready for reproducible benchmarking" if all_met else "Some requirements not met",
    }


def generate_environment_report(
    output_path: Optional[str] = None,
) -> str:
    """
    Generate environment validation report.
    
    Args:
        output_path: Optional path to save report
        
    Returns:
        Markdown report string
    """
    validation = validate_environment()
    reproducibility = check_reproducibility_requirements()
    
    lines = [
        "# Environment Validation Report",
        "",
        f"**Status**: {validation['status'].upper()}",
        f"**Checks Passed**: {validation['summary']['passed']}/{validation['summary']['total']}",
        "",
        "## Validation Checks",
        "",
        "| Check | Value | Status |",
        "|-------|-------|--------|",
    ]
    
    for check in validation["checks"]:
        status = "✓" if check["passed"] else "✗"
        lines.append(f"| {check['name']} | {check['value']} | {status} |")
    
    lines.append("")
    
    if validation["errors"]:
        lines.extend([
            "## Errors",
            "",
        ])
        for error in validation["errors"]:
            lines.append(f"- ❌ {error}")
        lines.append("")
    
    if validation["warnings"]:
        lines.extend([
            "## Warnings",
            "",
        ])
        for warning in validation["warnings"]:
            lines.append(f"- ⚠️ {warning}")
        lines.append("")
    
    lines.extend([
        "## Reproducibility Requirements",
        "",
        f"**Ready**: {'Yes' if reproducibility['ready'] else 'No'}",
        "",
        "| Requirement | Current | Recommended | Met |",
        "|-------------|---------|-------------|-----|",
    ])
    
    for req in reproducibility["requirements"]:
        met = "✓" if req["met"] else "✗"
        lines.append(f"| {req['name']} | {req['current']} | {req['recommended']} | {met} |")
    
    lines.append("")
    
    if reproducibility["recommendations"]:
        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in reproducibility["recommendations"]:
            lines.append(f"- {rec}")
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
    
    return report
