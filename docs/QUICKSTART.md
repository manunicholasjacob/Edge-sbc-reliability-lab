# Quick Start Guide

Get up and running with Edge SBC Reliability Lab in minutes.

## Prerequisites

- Raspberry Pi 5 (4GB or 8GB recommended)
- Raspberry Pi OS (Debian Bookworm)
- Python 3.9+
- At least one inference runtime installed

## Installation

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/edge-sbc-reliability-lab.git
cd edge-sbc-reliability-lab

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .
```

### 2. Install Inference Runtimes

Install at least one runtime:

```bash
# ONNX Runtime (recommended)
pip install onnxruntime

# TensorFlow Lite
pip install tflite-runtime

# PyTorch (larger download)
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 3. Verify Installation

```bash
# Check system info and available runtimes
sbc-bench info
```

## Your First Benchmark

### 1. Prepare a Model

Download or convert a model. For testing, you can create a dummy model:

```python
# create_test_model.py
import numpy as np

# Create dummy ONNX model
from edge_sbc_reliability_lab.inference.model_loader import create_dummy_onnx_model

create_dummy_onnx_model(
    "models/test_model.onnx",
    input_shape=(1, 3, 224, 224)
)
print("Created models/test_model.onnx")
```

Or download MobileNetV2:
```bash
mkdir -p models
# Download from ONNX Model Zoo or convert from TensorFlow
```

### 2. Run Health Check

```bash
sbc-bench health-check --model models/test_model.onnx
```

### 3. Run Quick Benchmark

```bash
# Quick burst benchmark (100 iterations)
sbc-bench run --model models/test_model.onnx --runtime onnx --runs 100
```

### 4. View Results

```bash
# List results
ls results/

# Analyze latest run
sbc-bench analyze results/$(ls -t results | head -1)
```

## Common Workflows

### Quick Performance Test

```bash
sbc-bench run --model model.onnx --runs 500
```

### Sustained Thermal Test (10 minutes)

```bash
sbc-bench run --model model.onnx --duration 600
```

### Compare Runtimes

```bash
# Run ONNX benchmark
sbc-bench run --model model.onnx --runtime onnx --runs 500

# Run TFLite benchmark
sbc-bench run --model model.tflite --runtime tflite --runs 500

# Compare results
sbc-bench compare results/run1 results/run2
```

### Full Benchmark Suite

```bash
sbc-bench pack --config configs/benchmark_pack_standard.yaml
```

## Configuration Files

Create a YAML config for repeatable benchmarks:

```yaml
# configs/my_benchmark.yaml
experiment_name: "my_test"
model_path: "models/my_model.onnx"
runtime: "onnx"

warmup_runs: 20
measured_runs: 500
threads: 4

collect_temperature: true
generate_plots: true
```

Run with:
```bash
sbc-bench run --config configs/my_benchmark.yaml
```

## Optimizing Results

### Set CPU Governor

For consistent results:
```bash
sudo cpufreq-set -g performance
```

### Ensure Cool Start

Wait for temperature to drop below 50°C:
```bash
# Check current temperature
cat /sys/class/thermal/thermal_zone0/temp
# Divide by 1000 for °C
```

### Minimize Background Load

```bash
# Check CPU usage
htop

# Stop unnecessary services
sudo systemctl stop bluetooth
sudo systemctl stop cups
```

## Troubleshooting

### "Runtime not available"

Install the required runtime:
```bash
pip install onnxruntime  # or tflite-runtime, torch
```

### High Variability

- Set CPU governor to `performance`
- Close background applications
- Check power supply

### Thermal Throttling

- Improve cooling (add heatsink/fan)
- Wait for cooldown between runs
- Reduce benchmark duration

### Permission Errors

Some features require root access:
```bash
# For governor changes
sudo cpufreq-set -g performance

# For vcgencmd (usually works without sudo)
vcgencmd measure_temp
```

## Next Steps

- Read [METHODOLOGY.md](METHODOLOGY.md) for benchmarking best practices
- Explore [ARCHITECTURE.md](ARCHITECTURE.md) for framework details
- Check sample configs in `configs/` directory
- Run the full benchmark pack for comprehensive analysis
