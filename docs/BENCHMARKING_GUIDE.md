# Benchmarking Guide

This guide explains how to run fair, reproducible benchmarks on Raspberry Pi 5.

## Before You Start

### Hardware Setup

1. **Cooling**: Use adequate cooling (heatsink minimum, active cooler recommended)
2. **Power**: Use official 5V/5A USB-C power supply
3. **Storage**: Use fast SD card or NVMe for consistent I/O
4. **Peripherals**: Disconnect unnecessary USB devices

### Software Setup

```bash
# Install the package
pip install -e .

# Verify installation
sbc-bench info

# Run health check
sbc-bench health-check
```

### System Configuration

```bash
# Set CPU governor to performance (recommended)
sudo cpufreq-set -g performance

# Verify governor
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

## Running Benchmarks

### Quick Start

```bash
# Simple benchmark with defaults
sbc-bench run --model models/model.onnx --runtime onnx --runs 100

# From config file
sbc-bench run --config configs/pi5_onnx_burst.yaml
```

### Benchmark Modes

#### Burst Mode (Fixed Iterations)

Best for quick performance snapshots:

```bash
sbc-bench run --model model.onnx --runs 500
```

#### Sustained Mode (Duration-Based)

Best for thermal drift analysis:

```bash
sbc-bench run --model model.onnx --duration 600  # 10 minutes
```

#### Benchmark Pack

Run standardized suite:

```bash
sbc-bench pack --config configs/benchmark_pack_standard.yaml
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--model` | Path to model file | Required |
| `--runtime` | Runtime (onnx, tflite, torch) | onnx |
| `--runs` | Number of measured iterations | 100 |
| `--duration` | Sustained duration (seconds) | 0 |
| `--warmup` | Warmup iterations | 10 |
| `--threads` | CPU threads | 4 |
| `--batch` | Batch size | 1 |
| `--output` | Output directory | results |

## Fair Benchmarking

### Pre-Run Checklist

- [ ] CPU temperature < 50°C
- [ ] CPU governor set to "performance"
- [ ] No heavy background processes
- [ ] Adequate disk space
- [ ] Model file accessible

### Thermal Considerations

1. **Cool start**: Wait for temperature to drop below 50°C
2. **Consistent ambient**: Note room temperature
3. **Cooldown between runs**: Wait 2-3 minutes

### Comparing Runs

Use the fairness checker:

```bash
sbc-bench compare results/run1 results/run2
```

Runs are comparable when:
- Same model and runtime
- Same batch size and threads
- Similar starting temperature
- Same CPU governor

## Interpreting Results

### Key Metrics

| Metric | Description | Good Value |
|--------|-------------|------------|
| Mean Latency | Average inference time | Lower is better |
| P99 Latency | 99th percentile | Close to mean |
| Throughput | Inferences per second | Higher is better |
| CV | Coefficient of variation | < 0.1 |
| Drift % | Latency change over time | < 5% |
| Stability Score | Composite stability metric | > 80 |

### Understanding Output

```json
{
  "latency": {
    "mean_ms": 12.5,
    "p50_ms": 12.3,
    "p99_ms": 15.2,
    "throughput_infs_per_sec": 80.0
  },
  "thermal": {
    "start_c": 45.0,
    "end_c": 58.0,
    "rise_c": 13.0
  },
  "stability_score": 85.0
}
```

### Warning Signs

- **High CV (> 0.2)**: Inconsistent performance
- **Large drift (> 10%)**: Thermal issues
- **Throttling detected**: Improve cooling
- **Low stability score (< 50)**: Review setup

## Advanced Usage

### Custom Configuration

Create a YAML config:

```yaml
experiment_name: "my_benchmark"
model_path: "models/my_model.onnx"
runtime: "onnx"

warmup_runs: 20
measured_runs: 1000
threads: 4

collect_temperature: true
collect_frequency: true

cooling_setup_note: "Active cooler at 50% speed"
ambient_note: "Air-conditioned room, ~22°C"
```

### Python API

```python
from edge_sbc_reliability_lab import ExperimentConfig, BenchmarkRunner

config = ExperimentConfig(
    experiment_name="api_test",
    model_path="model.onnx",
    runtime="onnx",
    measured_runs=500,
)

runner = BenchmarkRunner(config)
result = runner.run()

print(f"Mean: {result['summary']['latency']['mean_ms']:.2f} ms")
```

### Analysis

```bash
# Summarize results
sbc-bench analyze results/run_dir/

# Compare multiple runs
sbc-bench compare results/run1 results/run2 results/run3

# Generate leaderboard
python -m edge_sbc_reliability_lab.analysis.build_leaderboard results/
```

## Troubleshooting

### High Variability

- Set CPU governor to "performance"
- Close background applications
- Check for thermal throttling

### Thermal Throttling

- Improve cooling solution
- Reduce ambient temperature
- Add cooldown periods

### Inconsistent Results

- Ensure consistent starting temperature
- Use longer warmup period
- Check power supply quality

### Runtime Errors

- Verify model file format
- Check runtime installation
- Review error logs in output directory
