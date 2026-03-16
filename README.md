# Edge SBC Reliability Lab

**A research-grade benchmarking and reliability framework for AI inference on Raspberry Pi 5**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Raspberry Pi 5](https://img.shields.io/badge/Raspberry%20Pi-5-C51A4A.svg)](https://www.raspberrypi.com/products/raspberry-pi-5/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0007--6589--6572-green.svg)](https://orcid.org/0009-0007-6589-6572)

## Overview

Edge SBC Reliability Lab is a comprehensive toolkit for evaluating AI inference performance, thermal behavior, and long-term reliability on edge devices. While designed specifically for **Raspberry Pi 5**, the framework provides insights applicable to edge AI deployment scenarios.

### Key Features

- **Multi-Runtime Support**: ONNX Runtime, TensorFlow Lite, and PyTorch
- **Thermal Drift Analysis**: Correlate latency changes with temperature over time
- **Sustained Workload Testing**: 10-60+ minute benchmarks for reliability assessment
- **Reproducibility Framework**: Manifests, environment validation, and fair comparison checks
- **Publication-Quality Output**: Structured JSON/CSV results, statistical analysis, and visualizations

### What This Framework Measures

| Metric | Description |
|--------|-------------|
| **Latency Distribution** | Mean, median, P50/P90/P95/P99 percentiles |
| **Throughput** | Inferences per second under various conditions |
| **Thermal Behavior** | Temperature rise, throttling detection, cooldown patterns |
| **Performance Drift** | Latency changes over sustained workloads |
| **Stability Score** | Composite metric combining variability, drift, and thermal impact |

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/manunicholasjacob/Edge-sbc-reliability-lab.git
cd Edge-sbc-reliability-lab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run a quick benchmark
sbc-bench run --model models/mobilenetv2.onnx --runtime onnx --runs 100

# Run from config file
sbc-bench run --config configs/pi5_onnx_burst.yaml

# Run sustained benchmark (10 minutes)
sbc-bench run --model models/mobilenetv2.onnx --duration 600

# Pre-run health check
sbc-bench health-check

# Analyze results
sbc-bench analyze results/2024-03-16_benchmark_run001/

# Compare multiple runs
sbc-bench compare results/run1 results/run2
```

### Python API

```python
from edge_sbc_reliability_lab.core.config import ExperimentConfig
from edge_sbc_reliability_lab.core.runner import BenchmarkRunner

# Create configuration
config = ExperimentConfig(
    experiment_name="my_benchmark",
    model_name="mobilenetv2",
    model_path="models/mobilenetv2.onnx",
    runtime="onnx",
    warmup_runs=20,
    measured_runs=500,
    threads=4,
)

# Run benchmark
runner = BenchmarkRunner(config)
result = runner.run()

print(f"Mean latency: {result['summary']['latency']['mean_ms']:.2f} ms")
print(f"Throughput: {result['summary']['latency']['throughput_infs_per_sec']:.1f} inf/s")
```

## Benchmark Modes

### Burst Mode
Quick performance snapshot with fixed iterations:
```bash
sbc-bench run --model model.onnx --runs 500
```

### Sustained Mode
Long-duration test for thermal drift analysis:
```bash
sbc-bench run --model model.onnx --duration 600  # 10 minutes
```

### Benchmark Pack
Run standardized benchmark suite:
```bash
sbc-bench pack --config configs/benchmark_pack_standard.yaml
```

## Output Structure

Each benchmark run creates a structured output directory:

```
results/
└── 2024-03-16_120000_pi5_onnx_burst/
    ├── config_resolved.yaml      # Full configuration
    ├── system_snapshot.json      # Hardware/software environment
    ├── latency_samples.csv       # Raw latency measurements
    ├── thermal_trace.csv         # Temperature over time
    ├── frequency_trace.csv       # CPU frequency over time
    ├── summary.json              # Statistical summary
    ├── manifest.json             # Reproducibility manifest
    ├── warnings.json             # Any warnings generated
    └── figures/
        ├── latency_distribution.png
        ├── latency_over_time.png
        └── temperature_over_time.png
```

## Configuration

### YAML Configuration Example

```yaml
experiment_name: "pi5_onnx_sustained"
model_name: "mobilenetv2"
model_path: "models/mobilenetv2.onnx"
runtime: "onnx"

warmup_runs: 20
measured_runs: 0
sustained_duration_sec: 600
batch_size: 1
threads: 4

collect_temperature: true
collect_frequency: true
thermal_sample_interval_sec: 1.0

output_dir: "results"
save_raw_latencies: true
generate_plots: true

cooling_setup_note: "Passive heatsink"
ambient_note: "Room temperature ~22°C"
```

## Analysis Tools

### Summarize Results
```bash
sbc-bench analyze results/run_dir/ --format markdown
```

### Compare Runtimes
```bash
sbc-bench compare results/onnx_run results/tflite_run --format markdown
```

### Generate Leaderboard
```python
from edge_sbc_reliability_lab.analysis.build_leaderboard import generate_leaderboard_report

report = generate_leaderboard_report(
    run_dirs=["results/run1", "results/run2", "results/run3"],
    output_path="leaderboard.md"
)
```

## Reproducibility

### Environment Validation
```bash
sbc-bench health-check
```

### Manifest Verification
```python
from edge_sbc_reliability_lab.reproducibility import verify_manifest

result = verify_manifest("results/run_dir/")
print(f"Verified: {result['verified']}")
```

### Fair Comparison Check
```python
from edge_sbc_reliability_lab.analysis.fairness_checker import check_fairness

result = check_fairness(["results/run1", "results/run2"])
print(f"Comparable: {result['comparable']}")
```

## Hardware Requirements

### Tested Platform
- **Raspberry Pi 5** (4GB or 8GB)
- Raspberry Pi OS (Debian Bookworm)
- Python 3.9+

### Recommended Setup
- Passive heatsink (minimum) or active cooling
- Stable 5V/5A USB-C power supply
- Adequate ventilation

## Limitations

This framework provides **relative performance comparisons** and **reliability insights**, not absolute benchmarks. Key limitations:

- **Power estimation is proxy-based**: Uses CPU utilization model, not actual power measurement. For accurate power data, use external instrumentation (INA219, USB power meter).
- **Single-board focus**: Optimized for Raspberry Pi 5. Other platforms may require adaptation.
- **Model-dependent**: Results vary significantly by model architecture and size.
- **Environmental sensitivity**: Temperature, background load, and power supply affect results.

## Project Structure

```
edge-sbc-reliability-lab/
├── src/edge_sbc_reliability_lab/
│   ├── core/           # Config, logging, statistics, output management
│   ├── inference/      # Runtime interfaces (ONNX, TFLite, PyTorch)
│   ├── thermal/        # Temperature/frequency logging, drift analysis
│   ├── power/          # Power proxy estimation, external trace import
│   ├── platform/       # System snapshot, Pi metadata, governor check
│   ├── workloads/      # Burst, sustained, mixed load runners
│   ├── analysis/       # Summarization, comparison, reliability scoring
│   ├── reproducibility/# Environment validation, manifests
│   └── scripts/        # Health check, benchmark pack runner
├── configs/            # Sample configuration files
├── docs/               # Documentation
├── tests/              # Test suite
└── results/            # Benchmark outputs (gitignored)
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## Citation

If you use this framework in research, please cite:

```bibtex
@software{edge_sbc_reliability_lab,
  title = {Edge SBC Reliability Lab: Benchmarking Framework for AI Inference on Raspberry Pi},
  author = {Jacob, Manu Nicholas},
  year = {2024},
  url = {https://github.com/manunicholasjacob/Edge-sbc-reliability-lab}
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## About the Author

**Manu Nicholas Jacob** is a hardware engineer at Dell Technologies in Austin, TX, specializing in edge computing and SBC-based AI deployment. This project emerged from research into real-world reliability characteristics of AI inference on resource-constrained edge devices.

## Acknowledgments

- Raspberry Pi Foundation for the excellent Pi 5 hardware platform
- ONNX Runtime, TensorFlow, and PyTorch teams for robust inference runtimes
- The edge AI and embedded systems research community
