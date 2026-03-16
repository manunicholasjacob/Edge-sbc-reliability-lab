#!/usr/bin/env python3
"""
Main CLI for Edge SBC Reliability Lab.

Provides unified command-line interface for all benchmarking operations.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from edge_sbc_reliability_lab import __version__
from edge_sbc_reliability_lab.core.config import ExperimentConfig, load_config
from edge_sbc_reliability_lab.core.logging_utils import setup_logger
from edge_sbc_reliability_lab.core.runner import BenchmarkRunner


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="sbc-bench",
        description="Edge SBC Reliability Lab - Benchmarking toolkit for Raspberry Pi 5",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmark from config file
  sbc-bench run --config configs/pi5_onnx_resnet.yaml

  # Quick benchmark with inline options
  sbc-bench run --model model.onnx --runtime onnx --runs 100

  # Run sustained benchmark
  sbc-bench run --model model.onnx --duration 600

  # Run benchmark pack
  sbc-bench pack --config configs/benchmark_pack_pi5.yaml

  # Analyze results
  sbc-bench analyze results/2024-03-16_benchmark_run001/

  # Compare runs
  sbc-bench compare results/run1 results/run2

  # Health check
  sbc-bench health-check
        """
    )
    
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a benchmark")
    run_parser.add_argument("--config", "-c", help="Path to YAML config file")
    run_parser.add_argument("--model", "-m", help="Path to model file")
    run_parser.add_argument("--runtime", "-r", choices=["onnx", "tflite", "torch"], default="onnx")
    run_parser.add_argument("--runs", "-n", type=int, default=100, help="Number of measured runs")
    run_parser.add_argument("--duration", "-d", type=float, default=0, help="Sustained duration (seconds)")
    run_parser.add_argument("--warmup", "-w", type=int, default=10, help="Warmup runs")
    run_parser.add_argument("--batch-size", "-b", type=int, default=1)
    run_parser.add_argument("--threads", "-t", type=int, default=4)
    run_parser.add_argument("--output-dir", "-o", default="results")
    run_parser.add_argument("--name", help="Experiment name")
    run_parser.add_argument("--no-thermal", action="store_true", help="Disable thermal logging")
    run_parser.add_argument("--no-plots", action="store_true", help="Disable plot generation")
    run_parser.add_argument("--quiet", "-q", action="store_true")
    
    # Pack command (benchmark pack)
    pack_parser = subparsers.add_parser("pack", help="Run benchmark pack")
    pack_parser.add_argument("--config", "-c", help="Path to pack config file")
    pack_parser.add_argument("--output-dir", "-o", default="results")
    pack_parser.add_argument("--quick", action="store_true", help="Run quick version")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze benchmark results")
    analyze_parser.add_argument("run_dir", help="Path to run directory")
    analyze_parser.add_argument("--format", choices=["text", "markdown", "json"], default="text")
    analyze_parser.add_argument("--output", "-o", help="Output file path")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare multiple runs")
    compare_parser.add_argument("run_dirs", nargs="+", help="Paths to run directories")
    compare_parser.add_argument("--format", choices=["text", "markdown", "csv"], default="markdown")
    compare_parser.add_argument("--output", "-o", help="Output file path")
    
    # Health check command
    health_parser = subparsers.add_parser("health-check", help="Run pre-benchmark health check")
    health_parser.add_argument("--model", "-m", help="Model file to check")
    health_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show system information")
    info_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    # Set up logging
    log_level = "WARNING" if getattr(args, "quiet", False) else "INFO"
    logger = setup_logger(level=log_level if log_level == "WARNING" else 20)
    
    try:
        if args.command == "run":
            return cmd_run(args)
        elif args.command == "pack":
            return cmd_pack(args)
        elif args.command == "analyze":
            return cmd_analyze(args)
        elif args.command == "compare":
            return cmd_compare(args)
        elif args.command == "health-check":
            return cmd_health_check(args)
        elif args.command == "info":
            return cmd_info(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_run(args) -> int:
    """Execute run command."""
    # Load or create config
    if args.config:
        config = load_config(args.config)
    else:
        if not args.model:
            print("Error: Either --config or --model is required", file=sys.stderr)
            return 1
        
        config = ExperimentConfig(
            experiment_name=args.name or Path(args.model).stem,
            model_name=Path(args.model).stem,
            model_path=args.model,
            runtime=args.runtime,
            warmup_runs=args.warmup,
            measured_runs=args.runs,
            sustained_duration_sec=args.duration,
            batch_size=args.batch_size,
            threads=args.threads,
            output_dir=args.output_dir,
            collect_temperature=not args.no_thermal,
            collect_frequency=not args.no_thermal,
            generate_plots=not args.no_plots,
        )
    
    # Run benchmark
    runner = BenchmarkRunner(config)
    result = runner.run()
    
    if not args.quiet:
        print(f"\n{'='*60}")
        print("Benchmark Complete")
        print(f"{'='*60}")
        print(f"Success: {result['success']}")
        print(f"Duration: {result['duration_sec']:.1f}s")
        print(f"Results: {result['run_dir']}")
        
        if result.get("warnings"):
            print(f"\nWarnings ({len(result['warnings'])}):")
            for w in result["warnings"]:
                print(f"  - {w}")
    
    return 0 if result["success"] else 1


def cmd_pack(args) -> int:
    """Execute benchmark pack command."""
    from edge_sbc_reliability_lab.scripts.run_benchmark_pack import run_benchmark_pack
    
    result = run_benchmark_pack(
        config_path=args.config,
        output_dir=args.output_dir,
        quick=args.quick,
    )
    
    return 0 if result.get("success", False) else 1


def cmd_analyze(args) -> int:
    """Execute analyze command."""
    from edge_sbc_reliability_lab.analysis.summarize_results import summarize_run, generate_summary_report
    
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
        return 1
    
    if args.format == "json":
        import json
        summary = summarize_run(run_dir)
        output = json.dumps(summary, indent=2, default=str)
    else:
        output = generate_summary_report(run_dir, args.format)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Analysis saved to: {args.output}")
    else:
        print(output)
    
    return 0


def cmd_compare(args) -> int:
    """Execute compare command."""
    from edge_sbc_reliability_lab.analysis.runtime_comparison import generate_comparison_table
    
    run_dirs = [Path(d) for d in args.run_dirs]
    
    for d in run_dirs:
        if not d.exists():
            print(f"Error: Run directory not found: {d}", file=sys.stderr)
            return 1
    
    output = generate_comparison_table(run_dirs, format=args.format)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Comparison saved to: {args.output}")
    else:
        print(output)
    
    return 0


def cmd_health_check(args) -> int:
    """Execute health check command."""
    from edge_sbc_reliability_lab.scripts.pre_run_health_check import run_health_check
    
    result = run_health_check(model_path=args.model)
    
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    else:
        print(f"\n{'='*60}")
        print("Pre-Run Health Check")
        print(f"{'='*60}")
        print(f"Status: {result['status'].upper()}")
        print(f"\nChecks:")
        for check in result.get("checks", []):
            status_icon = "✓" if check["passed"] else "✗"
            print(f"  {status_icon} {check['name']}: {check['message']}")
        
        if result.get("warnings"):
            print(f"\nWarnings:")
            for w in result["warnings"]:
                print(f"  ⚠ {w}")
        
        if result.get("recommendations"):
            print(f"\nRecommendations:")
            for r in result["recommendations"]:
                print(f"  → {r}")
    
    return 0 if result["status"] == "pass" else 1


def cmd_info(args) -> int:
    """Execute info command."""
    from edge_sbc_reliability_lab.platform.system_snapshot import capture_system_snapshot
    from edge_sbc_reliability_lab.platform.pi_metadata import get_pi_info
    from edge_sbc_reliability_lab.inference.runtime_interface import list_available_runtimes, check_runtime_available
    
    snapshot = capture_system_snapshot()
    pi_info = get_pi_info()
    runtimes = list_available_runtimes()
    
    if args.json:
        import json
        info = {
            "system": snapshot.to_dict(),
            "pi_info": pi_info,
            "available_runtimes": runtimes,
        }
        print(json.dumps(info, indent=2, default=str))
    else:
        print(f"\n{'='*60}")
        print("System Information")
        print(f"{'='*60}")
        print(f"Device: {snapshot.device_model}")
        print(f"OS: {snapshot.os_version}")
        print(f"Kernel: {snapshot.kernel_version}")
        print(f"Python: {snapshot.python_version}")
        print(f"\nCPU: {snapshot.cpu_model}")
        print(f"Cores: {snapshot.cpu_cores} ({snapshot.cpu_threads} threads)")
        print(f"RAM: {snapshot.ram_total_gb:.1f} GB")
        print(f"Governor: {snapshot.cpu_governor}")
        print(f"Temperature: {snapshot.cpu_temp_c:.1f}°C")
        
        print(f"\nAvailable Runtimes:")
        for rt in ["onnx", "tflite", "torch"]:
            available, version = check_runtime_available(rt)
            status = f"✓ {version}" if available else "✗ not installed"
            print(f"  {rt}: {status}")
        
        if pi_info.get("is_raspberry_pi"):
            print(f"\nRaspberry Pi Info:")
            print(f"  Model: {pi_info.get('model', 'Unknown')}")
            print(f"  Memory: {pi_info.get('memory_mb', 0)} MB")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
