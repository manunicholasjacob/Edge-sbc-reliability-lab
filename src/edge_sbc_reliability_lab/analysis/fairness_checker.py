"""
Fairness checker for benchmark comparisons.

Validates whether two or more benchmark runs are directly comparable
based on configuration and environmental conditions.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run


def check_fairness(
    run_dirs: List[Union[str, Path]],
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Check if benchmark runs are fairly comparable.
    
    Args:
        run_dirs: List of run directory paths
        strict: Use strict comparison criteria
        
    Returns:
        Dictionary with fairness assessment
    """
    if len(run_dirs) < 2:
        return {
            "comparable": True,
            "warnings": [],
            "differences": [],
            "message": "Single run - no comparison needed",
        }
    
    # Load all summaries
    summaries = []
    for run_dir in run_dirs:
        try:
            summaries.append(summarize_run(run_dir))
        except Exception as e:
            return {
                "comparable": False,
                "warnings": [f"Failed to load run: {run_dir} - {e}"],
                "differences": [],
                "message": "Could not load all runs for comparison",
            }
    
    warnings = []
    differences = []
    
    # Check configuration differences
    config_checks = [
        ("batch_size", "Batch size", True),
        ("threads", "Thread count", True),
        ("warmup_runs", "Warmup runs", False),
        ("runtime", "Runtime", True),
        ("model_name", "Model", True),
    ]
    
    for key, name, critical in config_checks:
        values = set()
        for s in summaries:
            config = s.get("config", {})
            values.add(str(config.get(key, "unknown")))
        
        if len(values) > 1:
            diff = {
                "field": name,
                "values": list(values),
                "critical": critical,
            }
            differences.append(diff)
            
            if critical:
                warnings.append(f"Different {name}: {', '.join(values)}")
    
    # Check environmental differences
    env_checks = [
        ("cpu_governor", "CPU Governor", True),
        ("cooling_note", "Cooling setup", False),
        ("ambient_note", "Ambient conditions", False),
    ]
    
    for key, name, critical in env_checks:
        values = set()
        for s in summaries:
            # Try config first, then system snapshot
            value = s.get("config", {}).get(key)
            if value is None:
                value = s.get("system", {}).get(key)
            values.add(str(value) if value else "unknown")
        
        if len(values) > 1:
            diff = {
                "field": name,
                "values": list(values),
                "critical": critical,
            }
            differences.append(diff)
            
            if critical:
                warnings.append(f"Different {name}: {', '.join(values)}")
    
    # Check starting temperature
    start_temps = []
    for s in summaries:
        thermal = s.get("thermal_summary", {})
        start_temp = thermal.get("start_c", 0)
        if start_temp > 0:
            start_temps.append(start_temp)
    
    if start_temps and len(start_temps) == len(summaries):
        temp_range = max(start_temps) - min(start_temps)
        if temp_range > 10:
            warnings.append(f"Large starting temperature difference: {temp_range:.1f}°C")
            differences.append({
                "field": "Starting temperature",
                "values": [f"{t:.1f}°C" for t in start_temps],
                "critical": True,
            })
        elif temp_range > 5:
            warnings.append(f"Moderate starting temperature difference: {temp_range:.1f}°C")
            differences.append({
                "field": "Starting temperature",
                "values": [f"{t:.1f}°C" for t in start_temps],
                "critical": False,
            })
    
    # Check for missing telemetry
    for i, s in enumerate(summaries):
        run_id = s.get("run_id", f"run_{i+1}")
        
        if "thermal_summary" not in s:
            warnings.append(f"{run_id}: Missing thermal data")
        
        if "latency_stats" not in s and "results" not in s:
            warnings.append(f"{run_id}: Missing latency data")
    
    # Determine comparability
    critical_diffs = [d for d in differences if d.get("critical")]
    
    if strict:
        comparable = len(differences) == 0
    else:
        comparable = len(critical_diffs) == 0
    
    # Generate message
    if comparable and not warnings:
        message = "Runs are directly comparable"
    elif comparable:
        message = "Runs are comparable with minor differences"
    else:
        message = "Runs may not be directly comparable due to configuration/environmental differences"
    
    return {
        "comparable": comparable,
        "warnings": warnings,
        "differences": differences,
        "critical_differences": len(critical_diffs),
        "total_differences": len(differences),
        "message": message,
        "runs_checked": len(summaries),
    }


def generate_fairness_report(
    run_dirs: List[Union[str, Path]],
    output_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Generate a fairness report for benchmark comparison.
    
    Args:
        run_dirs: List of run directory paths
        output_path: Optional path to save report
        
    Returns:
        Markdown report string
    """
    result = check_fairness(run_dirs)
    
    lines = [
        "# Benchmark Fairness Report",
        "",
        f"**Runs Compared**: {result['runs_checked']}",
        f"**Comparable**: {'Yes' if result['comparable'] else 'No'}",
        "",
        f"## Assessment",
        "",
        result["message"],
        "",
    ]
    
    if result["differences"]:
        lines.extend([
            "## Differences Detected",
            "",
            "| Field | Values | Critical |",
            "|-------|--------|----------|",
        ])
        
        for diff in result["differences"]:
            critical = "⚠️ Yes" if diff["critical"] else "No"
            values = ", ".join(diff["values"])
            lines.append(f"| {diff['field']} | {values} | {critical} |")
        
        lines.append("")
    
    if result["warnings"]:
        lines.extend([
            "## Warnings",
            "",
        ])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
    
    if result["comparable"]:
        lines.extend([
            "## Recommendation",
            "",
            "These runs can be compared directly. Results should be valid for relative performance analysis.",
        ])
    else:
        lines.extend([
            "## Recommendation",
            "",
            "These runs have significant differences that may affect comparison validity. Consider:",
            "- Re-running benchmarks with matching configurations",
            "- Documenting the differences when reporting results",
            "- Using caution when drawing conclusions from comparisons",
        ])
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
    
    return report


def get_comparison_warnings(
    run_dirs: List[Union[str, Path]],
) -> List[str]:
    """
    Get list of warnings for benchmark comparison.
    
    Args:
        run_dirs: List of run directory paths
        
    Returns:
        List of warning strings
    """
    result = check_fairness(run_dirs)
    return result.get("warnings", [])
