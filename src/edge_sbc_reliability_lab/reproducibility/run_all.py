#!/usr/bin/env python3
"""
Run all benchmarks script for complete benchmark suite execution.

Provides orchestration for running the complete benchmark suite
with proper sequencing, cooldown, and aggregate reporting.
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from edge_sbc_reliability_lab.core.config import ExperimentConfig, load_config
from edge_sbc_reliability_lab.core.logging_utils import get_logger, setup_logger
from edge_sbc_reliability_lab.core.output import OutputManager
from edge_sbc_reliability_lab.core.runner import BenchmarkRunner
from edge_sbc_reliability_lab.scripts.pre_run_health_check import run_health_check
from edge_sbc_reliability_lab.thermal.temp_logger import get_cpu_temperature, wait_for_cooldown


def run_all_benchmarks(
    config_dir: str = "configs",
    output_dir: str = "results",
    cooldown_temp_c: float = 50.0,
    cooldown_timeout_sec: float = 300.0,
    skip_health_check: bool = False,
) -> Dict[str, Any]:
    """
    Run all benchmark configurations in sequence.
    
    Args:
        config_dir: Directory containing config files
        output_dir: Output directory for results
        cooldown_temp_c: Target temperature for cooldown between runs
        cooldown_timeout_sec: Maximum cooldown wait time
        skip_health_check: Skip pre-run health check
        
    Returns:
        Dictionary with aggregate results
    """
    logger = get_logger("RunAll")
    
    # Find all config files
    config_path = Path(config_dir)
    if not config_path.exists():
        logger.error(f"Config directory not found: {config_dir}")
        return {"success": False, "error": "Config directory not found"}
    
    config_files = sorted(config_path.glob("*.yaml")) + sorted(config_path.glob("*.yml"))
    
    if not config_files:
        logger.error(f"No config files found in: {config_dir}")
        return {"success": False, "error": "No config files found"}
    
    logger.info(f"Found {len(config_files)} benchmark configurations")
    
    # Pre-run health check
    if not skip_health_check:
        logger.info("Running pre-benchmark health check...")
        health = run_health_check()
        
        if health["status"] == "fail":
            logger.error("Health check failed - aborting")
            for error in health.get("errors", []):
                logger.error(f"  {error}")
            return {"success": False, "error": "Health check failed", "health": health}
        
        if health["warnings"]:
            logger.warning("Health check warnings:")
            for warning in health["warnings"]:
                logger.warning(f"  {warning}")
    
    # Create aggregate output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    aggregate_dir = Path(output_dir) / f"{timestamp}_full_suite"
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    start_time = time.time()
    
    # Run each benchmark
    for i, config_file in enumerate(config_files):
        logger.info(f"\n{'='*60}")
        logger.info(f"Benchmark {i+1}/{len(config_files)}: {config_file.name}")
        logger.info(f"{'='*60}")
        
        # Wait for cooldown if not first run
        if i > 0:
            current_temp = get_cpu_temperature()
            if current_temp > cooldown_temp_c:
                logger.info(f"Waiting for cooldown (current: {current_temp:.1f}°C, target: {cooldown_temp_c}°C)...")
                
                def cooldown_callback(temp, elapsed):
                    if int(elapsed) % 30 == 0:
                        logger.info(f"  Temperature: {temp:.1f}°C, elapsed: {elapsed:.0f}s")
                
                success, final_temp = wait_for_cooldown(
                    cooldown_temp_c,
                    cooldown_timeout_sec,
                    check_interval_sec=10,
                    callback=cooldown_callback,
                )
                
                if not success:
                    logger.warning(f"Cooldown timeout - proceeding at {final_temp:.1f}°C")
        
        # Load and run config
        try:
            config = load_config(str(config_file))
            config.output_dir = str(aggregate_dir)
            
            runner = BenchmarkRunner(config)
            result = runner.run()
            
            results.append({
                "config_file": config_file.name,
                "success": result["success"],
                "run_dir": result["run_dir"],
                "duration_sec": result["duration_sec"],
                "summary": result.get("summary", {}),
                "warnings": result.get("warnings", []),
            })
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            results.append({
                "config_file": config_file.name,
                "success": False,
                "error": str(e),
            })
    
    total_time = time.time() - start_time
    
    # Generate aggregate summary
    aggregate_summary = {
        "suite_name": "full_benchmark_suite",
        "timestamp": timestamp,
        "output_dir": str(aggregate_dir),
        "total_duration_sec": total_time,
        "total_duration_min": total_time / 60,
        "benchmarks_run": len(results),
        "benchmarks_passed": sum(1 for r in results if r.get("success")),
        "benchmarks_failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }
    
    # Save aggregate summary
    summary_path = aggregate_dir / "suite_summary.json"
    with open(summary_path, "w") as f:
        json.dump(aggregate_summary, f, indent=2, default=str)
    
    # Generate aggregate report
    _generate_suite_report(aggregate_dir, aggregate_summary)
    
    logger.info(f"\n{'='*60}")
    logger.info("Full Benchmark Suite Complete")
    logger.info(f"{'='*60}")
    logger.info(f"Total time: {total_time/60:.1f} minutes")
    logger.info(f"Passed: {aggregate_summary['benchmarks_passed']}/{aggregate_summary['benchmarks_run']}")
    logger.info(f"Results: {aggregate_dir}")
    
    aggregate_summary["success"] = aggregate_summary["benchmarks_failed"] == 0
    return aggregate_summary


def _generate_suite_report(output_dir: Path, summary: Dict[str, Any]):
    """Generate markdown report for benchmark suite."""
    lines = [
        "# Full Benchmark Suite Report",
        "",
        f"**Date**: {summary['timestamp']}",
        f"**Duration**: {summary['total_duration_min']:.1f} minutes",
        f"**Benchmarks**: {summary['benchmarks_passed']}/{summary['benchmarks_run']} passed",
        "",
        "## Results Summary",
        "",
        "| Config | Status | Duration | Mean Latency | Throughput | Warnings |",
        "|--------|--------|----------|--------------|------------|----------|",
    ]
    
    for result in summary.get("results", []):
        config = result.get("config_file", "unknown")
        status = "✓ Pass" if result.get("success") else "✗ Fail"
        duration = f"{result.get('duration_sec', 0):.0f}s" if result.get("duration_sec") else "N/A"
        
        latency = result.get("summary", {}).get("latency", {})
        mean_ms = f"{latency.get('mean_ms', 0):.2f} ms" if latency else "N/A"
        throughput = f"{latency.get('throughput_infs_per_sec', 0):.1f}" if latency else "N/A"
        warnings = len(result.get("warnings", []))
        
        lines.append(f"| {config} | {status} | {duration} | {mean_ms} | {throughput} | {warnings} |")
    
    lines.extend([
        "",
        "## Individual Results",
        "",
    ])
    
    for result in summary.get("results", []):
        config = result.get("config_file", "unknown")
        lines.append(f"### {config}")
        lines.append("")
        
        if result.get("success"):
            lines.append(f"- **Run Directory**: `{result.get('run_dir', 'N/A')}`")
            
            latency = result.get("summary", {}).get("latency", {})
            if latency:
                lines.append(f"- **Mean Latency**: {latency.get('mean_ms', 0):.3f} ms")
                lines.append(f"- **P99 Latency**: {latency.get('p99_ms', 0):.3f} ms")
                lines.append(f"- **Throughput**: {latency.get('throughput_infs_per_sec', 0):.1f} inf/s")
            
            thermal = result.get("summary", {}).get("thermal", {})
            if thermal:
                lines.append(f"- **Temperature Rise**: {thermal.get('range_c', 0):.1f}°C")
        else:
            lines.append(f"- **Error**: {result.get('error', 'Unknown error')}")
        
        if result.get("warnings"):
            lines.append("- **Warnings**:")
            for w in result["warnings"]:
                lines.append(f"  - {w}")
        
        lines.append("")
    
    report_path = output_dir / "SUITE_REPORT.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run all benchmarks in sequence",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--config-dir", "-c", default="configs", help="Config directory")
    parser.add_argument("--output-dir", "-o", default="results", help="Output directory")
    parser.add_argument("--cooldown-temp", type=float, default=50.0, help="Cooldown target temperature")
    parser.add_argument("--cooldown-timeout", type=float, default=300.0, help="Cooldown timeout seconds")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip pre-run health check")
    
    args = parser.parse_args()
    
    setup_logger()
    
    result = run_all_benchmarks(
        config_dir=args.config_dir,
        output_dir=args.output_dir,
        cooldown_temp_c=args.cooldown_temp,
        cooldown_timeout_sec=args.cooldown_timeout,
        skip_health_check=args.skip_health_check,
    )
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
