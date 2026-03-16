# Reproducibility Guide

This document explains the reproducibility framework in Edge SBC Reliability Lab.

## Philosophy

Reproducibility is essential for credible benchmarking. This framework captures everything needed to reproduce and validate results:

- **Environment state** at time of measurement
- **Configuration** used for the experiment
- **Raw data** for independent analysis
- **Manifests** for verification

## Run Directory Structure

Each benchmark creates a structured output directory:

```
results/2024-03-16_120000_experiment_name/
├── config_resolved.yaml    # Full resolved configuration
├── system_snapshot.json    # Hardware/software environment
├── latency_samples.csv     # Raw latency measurements
├── thermal_trace.csv       # Temperature over time
├── frequency_trace.csv     # CPU frequency over time
├── summary.json            # Statistical summary
├── manifest.json           # Reproducibility manifest
├── warnings.json           # Any warnings generated
├── figures/                # Generated plots
│   ├── latency_distribution.png
│   ├── latency_over_time.png
│   └── temperature_over_time.png
└── logs/                   # Execution logs
    └── benchmark.log
```

## System Snapshot

Every run captures comprehensive system state:

```json
{
  "device_model": "Raspberry Pi 5 Model B Rev 1.0",
  "hostname": "raspberrypi",
  "os_version": "Debian GNU/Linux 12 (bookworm)",
  "kernel_version": "6.1.0-rpi7-rpi-v8",
  "python_version": "3.11.2",
  "cpu_model": "Cortex-A76",
  "cpu_cores": 4,
  "memory_gb": 8.0,
  "cpu_governor": "performance",
  "runtime_versions": {
    "onnxruntime": "1.18.1"
  },
  "timestamp": "2024-03-16T12:00:00Z",
  "git_commit": "abc123..."
}
```

## Manifest System

### Generation

Manifests are automatically generated for each run:

```python
from edge_sbc_reliability_lab.reproducibility import generate_manifest

manifest = generate_manifest("results/run_dir/")
```

### Contents

```json
{
  "manifest_version": "1.0",
  "generated_at": "2024-03-16T12:00:00Z",
  "run_dir": "/path/to/results/run_dir",
  "files": [
    {
      "path": "latency_samples.csv",
      "size_bytes": 12345,
      "sha256": "abc123..."
    }
  ],
  "config": { ... },
  "system_snapshot": { ... },
  "manifest_hash": "def456..."
}
```

### Verification

Verify run integrity against manifest:

```python
from edge_sbc_reliability_lab.reproducibility import verify_manifest

result = verify_manifest("results/run_dir/")
print(f"Verified: {result['verified']}")
print(f"Files checked: {result['verified_files']}/{result['total_files']}")
```

## Environment Validation

### Pre-Run Checks

Before benchmarking, validate the environment:

```bash
sbc-bench health-check
```

Checks include:
- CPU temperature (should be < 50°C)
- CPU governor (should be "performance")
- Available memory
- Disk space
- Required packages
- Thermal interface accessibility

### Validation Report

```json
{
  "status": "pass",
  "checks": [
    {"name": "CPU Temperature", "value": "45.2°C", "passed": true},
    {"name": "CPU Governor", "value": "performance", "passed": true},
    {"name": "Available Memory", "value": "6.2 GB", "passed": true}
  ],
  "recommendations": []
}
```

## Configuration System

### YAML Configuration

```yaml
experiment_name: "pi5_onnx_benchmark"
model_path: "models/mobilenetv2.onnx"
runtime: "onnx"

warmup_runs: 20
measured_runs: 500
threads: 4

collect_temperature: true
collect_frequency: true

cooling_setup_note: "Official active cooler"
ambient_note: "Room temperature ~22°C"
```

### Config Resolution

The framework resolves and saves the full configuration:

```python
from edge_sbc_reliability_lab.core.config import load_config

config = load_config("configs/my_benchmark.yaml")
# Defaults are filled in
# Paths are resolved
# Validation is performed
```

## Reproducing Results

### From Config File

```bash
sbc-bench run --config configs/original_config.yaml
```

### From Manifest

```python
# Load original manifest
with open("results/run_dir/manifest.json") as f:
    manifest = json.load(f)

# Recreate config
config = ExperimentConfig(**manifest["config"])

# Run benchmark
runner = BenchmarkRunner(config)
result = runner.run()
```

## Fair Comparison

### Fairness Checker

Before comparing runs, validate comparability:

```python
from edge_sbc_reliability_lab.analysis import check_fairness

result = check_fairness(["results/run1", "results/run2"])
if not result["comparable"]:
    print("Warning:", result["message"])
    for diff in result["differences"]:
        print(f"  - {diff['field']}: {diff['values']}")
```

### Comparability Criteria

Runs are comparable when they have:
- Same model (verified by hash if available)
- Same batch size and thread count
- Same runtime version
- Similar starting temperature (±5°C)
- Same CPU governor setting

## Best Practices

### Before Running

1. Set CPU governor to "performance"
2. Wait for cool starting temperature
3. Close unnecessary applications
4. Document cooling and ambient conditions

### During Development

1. Use version control for configs
2. Tag releases with benchmark results
3. Archive raw data, not just summaries
4. Document any manual steps

### For Publication

1. Include manifest hashes in papers
2. Archive results on Zenodo
3. Provide config files for reproduction
4. Document hardware setup completely

## Zenodo Integration

### Preparing a Release

1. Create a GitHub release with version tag
2. Include all config files used
3. Include sample results (or links)
4. Update CITATION.cff with version

### Archive Structure

```
edge-sbc-reliability-lab-v1.0.0/
├── configs/           # Experiment configurations
├── results/           # Sample benchmark results
├── docs/              # Documentation
├── CITATION.cff       # Citation metadata
└── README.md          # Overview
```

## Troubleshooting

### Manifest Verification Fails

- Check if files were modified after run
- Verify no files were deleted
- Re-run benchmark if data corrupted

### Environment Validation Fails

- Address each failed check
- Re-run validation after fixes
- Document any exceptions

### Results Not Reproducible

- Compare system snapshots
- Check for thermal differences
- Verify same software versions
- Consider hardware variability
