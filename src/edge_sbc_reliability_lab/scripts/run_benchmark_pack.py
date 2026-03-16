#!/usr/bin/env python3
"""
Benchmark pack runner for standardized benchmark suites.

Runs a curated set of benchmarks and generates aggregate reports.
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


# Default benchmark pack configuration
DEFAULT_PACK = {
    "name": "pi5_standard_pack",
    "description": "Standard Raspberry Pi 5 benchmark pack",
    "benchmarks": [
        {
            "name": "onnx_burst",
            "runtime": "onnx",
            "warmup_runs": 20,
            "measured_runs": 500,
            "sustained_duration_sec": 0,
            "description": "ONNX Runtime burst benchmark",
        },
        {
            "name": "onnx_sustained_5min",
            "runtime": "onnx",
            "warmup_runs": 20,
            "measured_runs": 0,
            "sustained_duration_sec": 300,
            "description": "ONNX Runtime 5-minute sustained benchmark",
        },
        {
            "name": "onnx_sustained_15min",
            "runtime": "onnx",
            "warmup_runs": 20,
            "measured_runs": 0,
            "sustained_duration_sec": 900,
            "description": "ONNX Runtime 15-minute sustained benchmark",
        },
        {
            "name": "tflite_burst",
            "runtime": "tflite",
            "warmup_runs": 20,
            "measured_runs": 500,
            "sustained_duration_sec": 0,
            "description": "TFLite burst benchmark",
        },
        {
            "name": "tflite_sustained_5min",
            "runtime": "tflite",
            "warmup_runs": 20,
            "measured_runs": 0,
            "sustained_duration_sec": 300,
            "description": "TFLite 5-minute sustained benchmark",
        },
        {
            "name": "thermal_stress_20min",
            "runtime": "onnx",
            "warmup_runs": 10,
            "measured_runs": 0,
            "sustained_duration_sec": 1200,
            "description": "20-minute thermal stress test",
        },
    ],
    "cooldown_between_sec": 60,
    "total_estimated_minutes": 55,
}

# Quick pack for faster testing
QUICK_PACK = {
    "name": "pi5_quick_pack",
    "description": "Quick Raspberry Pi 5 benchmark pack",
    "benchmarks": [
        {
            "name": "onnx_quick",
            "runtime": "onnx",
            "warmup_runs": 10,
            "measured_runs": 100,
            "sustained_duration_sec": 0,
            "description": "Quick ONNX benchmark",
        },
        {
            "name": "onnx_sustained_1min",
            "runtime": "onnx",
            "warmup_runs": 10,
            "measured_runs": 0,
            "sustained_duration_sec": 60,
            "description": "1-minute sustained benchmark",
        },
    ],
    "cooldown_between_sec": 30,
    "total_estimated_minutes": 5,
}


def run_benchmark_pack(
    config_path: Optional[str] = None,
    model_path: Optional[str] = None,
    output_dir: str = "results",
    quick: bool = False,
) -> Dict[str, Any]:
    """
    Run a benchmark pack.
    
    Args:
        config_path: Path to pack configuration YAML
        model_path: Path to model file
        output_dir: Output directory for results
        quick: Use quick pack instead of full pack
        
    Returns:
        Dictionary with pack results
    """
    logger = get_logger("BenchmarkPack")
    
    # Load pack configuration
    if config_path and Path(config_path).exists():
        pack_config = OutputManager.load_yaml(config_path)
    else:
        pack_config = QUICK_PACK if quick else DEFAULT_PACK
    
    pack_name = pack_config.get("name", "benchmark_pack")
    benchmarks = pack_config.get("benchmarks", [])
    cooldown_sec = pack_config.get("cooldown_between_sec", 60)
    
    logger.info(f"Starting benchmark pack: {pack_name}")
    logger.info(f"Benchmarks to run: {len(benchmarks)}")
    logger.info(f"Estimated time: {pack_config.get('total_estimated_minutes', 'unknown')} minutes")
    
    # Create pack output directory
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    pack_dir = Path(output_dir) / f"{timestamp}_{pack_name}"
    pack_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    start_time = time.time()
    
    for i, bench_config in enumerate(benchmarks):
        bench_name = bench_config.get("name", f"benchmark_{i+1}")
        logger.info(f"\n{'='*60}")
        logger.info(f"Running benchmark {i+1}/{len(benchmarks)}: {bench_name}")
        logger.info(f"{'='*60}")
        
        # Create experiment config
        config = ExperimentConfig(
            experiment_name=bench_name,
            model_name=Path(model_path).stem if model_path else "model",
            model_path=model_path or "",
            runtime=bench_config.get("runtime", "onnx"),
            warmup_runs=bench_config.get("warmup_runs", 10),
            measured_runs=bench_config.get("measured_runs", 100),
            sustained_duration_sec=bench_config.get("sustained_duration_sec", 0),
            threads=bench_config.get("threads", 4),
            batch_size=bench_config.get("batch_size", 1),
            output_dir=str(pack_dir),
            collect_temperature=True,
            collect_frequency=True,
            generate_plots=True,
        )
        
        # Run benchmark
        try:
            runner = BenchmarkRunner(config)
            result = runner.run()
            results.append({
                "name": bench_name,
                "success": result["success"],
                "run_dir": result["run_dir"],
                "duration_sec": result["duration_sec"],
                "summary": result.get("summary", {}),
            })
        except Exception as e:
            logger.error(f"Benchmark {bench_name} failed: {e}")
            results.append({
                "name": bench_name,
                "success": False,
                "error": str(e),
            })
        
        # Cooldown between benchmarks
        if i < len(benchmarks) - 1:
            logger.info(f"Cooling down for {cooldown_sec} seconds...")
            time.sleep(cooldown_sec)
    
    total_time = time.time() - start_time
    
    # Generate pack summary
    pack_summary = {
        "pack_name": pack_name,
        "pack_dir": str(pack_dir),
        "start_time": timestamp,
        "total_duration_sec": total_time,
        "total_duration_min": total_time / 60,
        "benchmarks_run": len(results),
        "benchmarks_passed": sum(1 for r in results if r.get("success")),
        "benchmarks_failed": sum(1 for r in results if not r.get("success")),
        "results": results,
    }
    
    # Save pack summary
    summary_path = pack_dir / "pack_summary.json"
    with open(summary_path, "w") as f:
        json.dump(pack_summary, f, indent=2, default=str)
    
    # Generate aggregate report
    _generate_pack_report(pack_dir, pack_summary)
    
    logger.info(f"\n{'='*60}")
    logger.info("Benchmark Pack Complete")
    logger.info(f"{'='*60}")
    logger.info(f"Total time: {total_time/60:.1f} minutes")
    logger.info(f"Passed: {pack_summary['benchmarks_passed']}/{pack_summary['benchmarks_run']}")
    logger.info(f"Results: {pack_dir}")
    
    pack_summary["success"] = pack_summary["benchmarks_failed"] == 0
    return pack_summary


def _generate_pack_report(pack_dir: Path, summary: Dict[str, Any]):
    """Generate markdown report for benchmark pack."""
    lines = [
        f"# Benchmark Pack Report: {summary['pack_name']}",
        "",
        f"**Date**: {summary['start_time']}",
        f"**Duration**: {summary['total_duration_min']:.1f} minutes",
        f"**Benchmarks**: {summary['benchmarks_passed']}/{summary['benchmarks_run']} passed",
        "",
        "## Results Summary",
        "",
        "| Benchmark | Status | Duration | Mean Latency | Throughput |",
        "|-----------|--------|----------|--------------|------------|",
    ]
    
    for result in summary.get("results", []):
        name = result.get("name", "unknown")
        status = "✓ Pass" if result.get("success") else "✗ Fail"
        duration = f"{result.get('duration_sec', 0):.0f}s"
        
        latency = result.get("summary", {}).get("latency", {})
        mean_ms = f"{latency.get('mean_ms', 0):.2f} ms" if latency else "N/A"
        throughput = f"{latency.get('throughput_infs_per_sec', 0):.1f} inf/s" if latency else "N/A"
        
        lines.append(f"| {name} | {status} | {duration} | {mean_ms} | {throughput} |")
    
    lines.extend([
        "",
        "## Individual Run Directories",
        "",
    ])
    
    for result in summary.get("results", []):
        if result.get("run_dir"):
            lines.append(f"- **{result['name']}**: `{result['run_dir']}`")
    
    report_path = pack_dir / "REPORT.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines))


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run benchmark pack",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--config", "-c", help="Path to pack configuration YAML")
    parser.add_argument("--model", "-m", help="Path to model file")
    parser.add_argument("--output-dir", "-o", default="results", help="Output directory")
    parser.add_argument("--quick", "-q", action="store_true", help="Run quick pack")
    
    args = parser.parse_args()
    
    setup_logger()
    
    result = run_benchmark_pack(
        config_path=args.config,
        model_path=args.model,
        output_dir=args.output_dir,
        quick=args.quick,
    )
    
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
