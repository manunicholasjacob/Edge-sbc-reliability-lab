#!/usr/bin/env python3
"""
Pre-run health check for benchmark validation.

Validates system state before running benchmarks to ensure
fair and reproducible results.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil


def run_health_check(
    model_path: Optional[str] = None,
    output_dir: str = "results",
    target_temp_c: float = 60.0,
) -> Dict[str, Any]:
    """
    Run comprehensive pre-benchmark health check.
    
    Args:
        model_path: Optional path to model file to validate
        output_dir: Output directory to check
        target_temp_c: Target starting temperature
        
    Returns:
        Dictionary with health check results
    """
    checks = []
    warnings = []
    recommendations = []
    
    # Check 1: Temperature
    temp = _get_cpu_temperature()
    temp_check = {
        "name": "CPU Temperature",
        "value": f"{temp:.1f}°C",
        "passed": temp < target_temp_c,
        "message": f"Current: {temp:.1f}°C (target: <{target_temp_c}°C)",
    }
    checks.append(temp_check)
    
    if temp >= 70:
        warnings.append(f"High CPU temperature: {temp:.1f}°C - results may be affected by throttling")
        recommendations.append("Wait for CPU to cool down or improve cooling")
    elif temp >= target_temp_c:
        warnings.append(f"Elevated temperature: {temp:.1f}°C - consider waiting for cooldown")
    
    # Check 2: CPU Governor
    governor = _get_cpu_governor()
    gov_check = {
        "name": "CPU Governor",
        "value": governor,
        "passed": governor == "performance",
        "message": f"Current: {governor}" + (" (recommended: performance)" if governor != "performance" else ""),
    }
    checks.append(gov_check)
    
    if governor != "performance":
        warnings.append(f"CPU governor is '{governor}', not 'performance'")
        recommendations.append("Set governor to performance: sudo cpufreq-set -g performance")
    
    # Check 3: Available Memory
    mem = psutil.virtual_memory()
    mem_available_gb = mem.available / (1024**3)
    mem_check = {
        "name": "Available Memory",
        "value": f"{mem_available_gb:.1f} GB",
        "passed": mem.percent < 80,
        "message": f"{mem_available_gb:.1f} GB available ({100 - mem.percent:.0f}% free)",
    }
    checks.append(mem_check)
    
    if mem.percent > 80:
        warnings.append(f"High memory usage: {mem.percent:.0f}%")
        recommendations.append("Close unnecessary applications to free memory")
    
    # Check 4: Disk Space
    disk = shutil.disk_usage(output_dir if os.path.exists(output_dir) else ".")
    disk_free_gb = disk.free / (1024**3)
    disk_check = {
        "name": "Disk Space",
        "value": f"{disk_free_gb:.1f} GB free",
        "passed": disk_free_gb > 1.0,
        "message": f"{disk_free_gb:.1f} GB available in output directory",
    }
    checks.append(disk_check)
    
    if disk_free_gb < 1.0:
        warnings.append(f"Low disk space: {disk_free_gb:.1f} GB")
        recommendations.append("Free up disk space before running benchmarks")
    
    # Check 5: Model File (if provided)
    if model_path:
        model_exists = os.path.isfile(model_path)
        model_check = {
            "name": "Model File",
            "value": model_path,
            "passed": model_exists,
            "message": "Found" if model_exists else "Not found",
        }
        checks.append(model_check)
        
        if not model_exists:
            warnings.append(f"Model file not found: {model_path}")
    
    # Check 6: Thermal Interface
    thermal_available = Path("/sys/class/thermal/thermal_zone0/temp").exists()
    thermal_check = {
        "name": "Thermal Monitoring",
        "value": "available" if thermal_available else "unavailable",
        "passed": thermal_available,
        "message": "Thermal interface accessible" if thermal_available else "Cannot read temperature",
    }
    checks.append(thermal_check)
    
    # Check 7: Background Load
    cpu_percent = psutil.cpu_percent(interval=0.5)
    load_check = {
        "name": "Background CPU Load",
        "value": f"{cpu_percent:.0f}%",
        "passed": cpu_percent < 20,
        "message": f"Current CPU usage: {cpu_percent:.0f}%",
    }
    checks.append(load_check)
    
    if cpu_percent > 30:
        warnings.append(f"High background CPU usage: {cpu_percent:.0f}%")
        recommendations.append("Close background applications for accurate benchmarks")
    
    # Check 8: Throttling Status
    throttle_status = _check_throttling()
    throttle_check = {
        "name": "Throttling Status",
        "value": "clear" if not throttle_status["any_active"] else "active",
        "passed": not throttle_status["any_active"],
        "message": "No throttling detected" if not throttle_status["any_active"] else "Throttling active",
    }
    checks.append(throttle_check)
    
    if throttle_status["any_active"]:
        warnings.append("Throttling is currently active")
        if throttle_status.get("under_voltage"):
            recommendations.append("Check power supply - under-voltage detected")
        if throttle_status.get("thermal"):
            recommendations.append("Improve cooling - thermal throttling active")
    
    # Check 9: Runtime Availability
    from edge_sbc_reliability_lab.inference.runtime_interface import list_available_runtimes
    runtimes = list_available_runtimes()
    runtime_check = {
        "name": "Inference Runtimes",
        "value": ", ".join(runtimes) if runtimes else "none",
        "passed": len(runtimes) > 0,
        "message": f"Available: {', '.join(runtimes)}" if runtimes else "No runtimes installed",
    }
    checks.append(runtime_check)
    
    if not runtimes:
        warnings.append("No inference runtimes available")
        recommendations.append("Install at least one runtime: pip install onnxruntime")
    
    # Determine overall status
    all_passed = all(c["passed"] for c in checks)
    critical_failed = any(
        not c["passed"] for c in checks 
        if c["name"] in ["Model File", "Inference Runtimes", "Disk Space"]
    )
    
    if critical_failed:
        status = "fail"
    elif all_passed:
        status = "pass"
    else:
        status = "warning"
    
    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "recommendations": recommendations,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["passed"]),
            "failed": sum(1 for c in checks if not c["passed"]),
        }
    }


def _get_cpu_temperature() -> float:
    """Get CPU temperature in Celsius."""
    thermal_path = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_path.exists():
        try:
            return int(thermal_path.read_text().strip()) / 1000.0
        except Exception:
            pass
    return 0.0


def _get_cpu_governor() -> str:
    """Get CPU governor."""
    gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    if gov_path.exists():
        try:
            return gov_path.read_text().strip()
        except Exception:
            pass
    return "unknown"


def _check_throttling() -> Dict[str, bool]:
    """Check throttling status."""
    import subprocess
    
    result = {
        "any_active": False,
        "under_voltage": False,
        "thermal": False,
        "frequency_capped": False,
    }
    
    try:
        proc = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0:
            import re
            match = re.search(r"throttled=0x([0-9a-fA-F]+)", proc.stdout)
            if match:
                flags = int(match.group(1), 16)
                result["under_voltage"] = bool(flags & 0x1)
                result["frequency_capped"] = bool(flags & 0x2)
                result["thermal"] = bool(flags & 0x4)
                result["any_active"] = bool(flags & 0xF)
    except Exception:
        pass
    
    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pre-run health check for benchmarks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--model", "-m", help="Model file to validate")
    parser.add_argument("--output-dir", "-o", default="results", help="Output directory")
    parser.add_argument("--target-temp", type=float, default=60.0, help="Target starting temperature")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    result = run_health_check(
        model_path=args.model,
        output_dir=args.output_dir,
        target_temp_c=args.target_temp,
    )
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print("Pre-Run Health Check")
        print(f"{'='*60}")
        print(f"Status: {result['status'].upper()}")
        print(f"\nChecks ({result['summary']['passed']}/{result['summary']['total_checks']} passed):")
        
        for check in result["checks"]:
            icon = "✓" if check["passed"] else "✗"
            print(f"  {icon} {check['name']}: {check['message']}")
        
        if result["warnings"]:
            print(f"\nWarnings:")
            for w in result["warnings"]:
                print(f"  ⚠ {w}")
        
        if result["recommendations"]:
            print(f"\nRecommendations:")
            for r in result["recommendations"]:
                print(f"  → {r}")
        
        print()
    
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    sys.exit(main())
