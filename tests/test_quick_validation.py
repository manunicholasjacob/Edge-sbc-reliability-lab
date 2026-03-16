#!/usr/bin/env python3
"""
Quick validation script to verify installation and basic functionality.

Run this to ensure the package is properly installed and working.
"""

import sys


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        import edge_sbc_reliability_lab
        print(f"  ✓ Package version: {edge_sbc_reliability_lab.__version__}")
    except ImportError as e:
        print(f"  ✗ Failed to import package: {e}")
        return False
    
    modules = [
        "edge_sbc_reliability_lab.core.config",
        "edge_sbc_reliability_lab.core.runner",
        "edge_sbc_reliability_lab.core.statistics",
        "edge_sbc_reliability_lab.core.output",
        "edge_sbc_reliability_lab.inference.runtime_interface",
        "edge_sbc_reliability_lab.inference.common",
        "edge_sbc_reliability_lab.thermal.temp_logger",
        "edge_sbc_reliability_lab.thermal.freq_logger",
        "edge_sbc_reliability_lab.thermal.drift_analysis",
        "edge_sbc_reliability_lab.platform.system_snapshot",
        "edge_sbc_reliability_lab.platform.pi_metadata",
        "edge_sbc_reliability_lab.power.utilization_power_proxy",
        "edge_sbc_reliability_lab.analysis.summarize_results",
        "edge_sbc_reliability_lab.workloads.sustained_runner",
        "edge_sbc_reliability_lab.reproducibility.environment_validator",
    ]
    
    for module in modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError as e:
            print(f"  ✗ {module}: {e}")
            return False
    
    return True


def test_runtimes():
    """Test available inference runtimes."""
    print("\nTesting inference runtimes...")
    
    from edge_sbc_reliability_lab.inference.runtime_interface import (
        list_available_runtimes,
        check_runtime_available,
    )
    
    available = list_available_runtimes()
    print(f"  Available runtimes: {available if available else 'none'}")
    
    for runtime in ["onnx", "tflite", "torch"]:
        is_available, version = check_runtime_available(runtime)
        status = f"✓ {version}" if is_available else "✗ not installed"
        print(f"  {runtime}: {status}")
    
    return len(available) > 0


def test_platform():
    """Test platform detection."""
    print("\nTesting platform detection...")
    
    from edge_sbc_reliability_lab.platform.pi_metadata import is_raspberry_pi, get_pi_model
    from edge_sbc_reliability_lab.thermal.temp_logger import get_cpu_temperature
    from edge_sbc_reliability_lab.thermal.freq_logger import get_cpu_frequency
    
    is_pi = is_raspberry_pi()
    print(f"  Raspberry Pi: {'Yes' if is_pi else 'No'}")
    
    if is_pi:
        model = get_pi_model()
        print(f"  Model: {model}")
    
    temp = get_cpu_temperature()
    print(f"  CPU Temperature: {temp:.1f}°C" if temp > 0 else "  CPU Temperature: unavailable")
    
    freq = get_cpu_frequency()
    print(f"  CPU Frequency: {freq:.0f} MHz" if freq > 0 else "  CPU Frequency: unavailable")
    
    return True


def test_statistics():
    """Test statistics computation."""
    print("\nTesting statistics...")
    
    from edge_sbc_reliability_lab.core.statistics import compute_latency_stats
    
    # Create sample latencies (10ms each, in nanoseconds)
    latencies_ns = [10_000_000 + i * 100_000 for i in range(100)]
    
    stats = compute_latency_stats(latencies_ns)
    
    print(f"  Sample count: {stats.count}")
    print(f"  Mean: {stats.mean_ms:.3f} ms")
    print(f"  P50: {stats.p50_ms:.3f} ms")
    print(f"  P99: {stats.p99_ms:.3f} ms")
    
    return stats.count == 100


def test_config():
    """Test configuration system."""
    print("\nTesting configuration...")
    
    from edge_sbc_reliability_lab.core.config import ExperimentConfig
    
    config = ExperimentConfig(
        experiment_name="validation_test",
        model_name="test_model",
        model_path="model.onnx",
        runtime="onnx",
        warmup_runs=5,
        measured_runs=10,
    )
    
    print(f"  Experiment: {config.experiment_name}")
    print(f"  Runtime: {config.runtime}")
    print(f"  Warmup runs: {config.warmup_runs}")
    print(f"  Measured runs: {config.measured_runs}")
    
    return True


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Edge SBC Reliability Lab - Quick Validation")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Runtimes", test_runtimes()))
    results.append(("Platform", test_platform()))
    results.append(("Statistics", test_statistics()))
    results.append(("Config", test_config()))
    
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("All validation tests passed!")
        return 0
    else:
        print("Some validation tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
