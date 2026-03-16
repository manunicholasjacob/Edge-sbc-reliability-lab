#!/usr/bin/env python3
"""Run a quick end-to-end benchmark test."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.runner import BenchmarkRunner

config = ExperimentConfig(
    experiment_name='quick_test',
    model_name='test_model',
    model_path='models/test_model.onnx',
    runtime='onnx',
    warmup_runs=5,
    measured_runs=50,
    threads=4,
    output_dir='results',
    collect_temperature=True,
    collect_frequency=True,
)

print("Running quick benchmark test...")
runner = BenchmarkRunner(config)
result = runner.run()

print()
print("=" * 50)
print("RESULTS")
print("=" * 50)
print(f"Success: {result['success']}")
print(f"Run dir: {result['run_dir']}")

if result['success']:
    latency = result['summary']['latency']
    print(f"Mean latency: {latency['mean_ms']:.3f} ms")
    print(f"P50 latency: {latency['p50_ms']:.3f} ms")
    print(f"P99 latency: {latency['p99_ms']:.3f} ms")
    print(f"Throughput: {latency['throughput_infs_per_sec']:.1f} inf/s")
    
    if 'thermal' in result['summary']:
        thermal = result['summary']['thermal']
        print(f"Temp start: {thermal.get('start_c', 0):.1f}°C")
        print(f"Temp end: {thermal.get('end_c', 0):.1f}°C")
else:
    print(f"Error: {result.get('error', 'Unknown')}")
