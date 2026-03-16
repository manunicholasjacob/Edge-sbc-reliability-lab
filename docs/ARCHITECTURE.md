# Architecture Overview

This document describes the architecture of Edge SBC Reliability Lab.

## System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI / API                                │
│                      (sbc-bench command)                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Core Runner                                  │
│  - Orchestrates benchmark execution                              │
│  - Manages telemetry collection                                  │
│  - Generates results and manifests                               │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Inference   │     │    Thermal    │     │    Platform   │
│   Harness     │     │   Monitoring  │     │    Capture    │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ - ONNX Runtime│     │ - Temp Logger │     │ - System Info │
│ - TFLite      │     │ - Freq Logger │     │ - Pi Metadata │
│ - PyTorch     │     │ - Throttle    │     │ - Governor    │
└───────────────┘     └───────────────┘     └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Output Manager                               │
│  - Structured directory creation                                 │
│  - JSON/CSV/YAML serialization                                   │
│  - Manifest generation                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Analysis Module                              │
│  - Statistical summaries                                         │
│  - Runtime comparison                                            │
│  - Thermal drift analysis                                        │
│  - Reliability scoring                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Core (`core/`)

The foundation of the framework:

- **config.py**: Experiment configuration dataclass with YAML loading/saving
- **runner.py**: Main benchmark orchestrator
- **statistics.py**: Latency statistics, drift metrics, stability scoring
- **output.py**: Output directory management and file serialization
- **timestamps.py**: Monotonic timestamp management
- **logging_utils.py**: Consistent logging configuration

### Inference (`inference/`)

Multi-runtime inference support:

- **runtime_interface.py**: Abstract interface and implementations for ONNX, TFLite, PyTorch
- **common.py**: Shared utilities (input generation, timing)
- **run_onnx.py**: ONNX Runtime benchmark runner
- **run_tflite.py**: TFLite benchmark runner
- **run_torch.py**: PyTorch benchmark runner
- **model_loader.py**: Model validation and metadata extraction

### Thermal (`thermal/`)

Temperature and frequency monitoring:

- **temp_logger.py**: Background temperature logging
- **freq_logger.py**: CPU frequency logging
- **throttle_detector.py**: Throttling detection via vcgencmd
- **drift_analysis.py**: Latency-temperature correlation analysis

### Platform (`platform/`)

System information capture:

- **system_snapshot.py**: Comprehensive system state capture
- **pi_metadata.py**: Raspberry Pi-specific information
- **governor_check.py**: CPU governor validation
- **environment_capture.py**: Runtime environment details

### Power (`power/`)

Power estimation (proxy-based):

- **utilization_power_proxy.py**: CPU-based power estimation
- **external_meter_adapter.py**: Import external power traces
- **energy_analysis.py**: Energy metrics computation

### Workloads (`workloads/`)

Different benchmark modes:

- **burst_runner.py**: Fixed-iteration burst benchmarks
- **sustained_runner.py**: Duration-based sustained benchmarks
- **mixed_load_runner.py**: Benchmarks with background CPU load
- **stress_background.py**: Background load generation

### Analysis (`analysis/`)

Post-run analysis tools:

- **summarize_results.py**: Result summarization
- **runtime_comparison.py**: Cross-runtime comparison
- **latency_vs_temp.py**: Thermal correlation analysis
- **sustained_drift.py**: Long-term drift analysis
- **reliability_summary.py**: Reliability scoring
- **fairness_checker.py**: Comparison validity checking
- **build_leaderboard.py**: Aggregate leaderboard generation

### Reproducibility (`reproducibility/`)

Reproducibility framework:

- **environment_validator.py**: Pre-run environment validation
- **manifest_generator.py**: Manifest creation and verification
- **run_all.py**: Full suite orchestration

## Data Flow

1. **Configuration Loading**: YAML config → ExperimentConfig dataclass
2. **Pre-Run Checks**: Environment validation, health check
3. **System Capture**: Hardware/software snapshot
4. **Monitoring Start**: Temperature, frequency loggers begin
5. **Warmup Phase**: Initial inferences (not measured)
6. **Measurement Phase**: Timed inferences with telemetry
7. **Monitoring Stop**: Collect all samples
8. **Statistics Computation**: Latency stats, drift metrics
9. **Output Generation**: JSON/CSV files, plots, manifest
10. **Analysis**: Post-run summarization and comparison

## Configuration System

Configurations are hierarchical:

```yaml
# Required
experiment_name: "my_benchmark"
model_path: "model.onnx"
runtime: "onnx"

# Benchmark parameters (with defaults)
warmup_runs: 10
measured_runs: 100
sustained_duration_sec: 0
batch_size: 1
threads: 4

# Telemetry (with defaults)
collect_temperature: true
thermal_sample_interval_sec: 1.0

# Output (with defaults)
output_dir: "results"
save_raw_latencies: true
generate_plots: true
```

## Output Format

### Directory Structure

```
results/TIMESTAMP_EXPERIMENT_NAME/
├── config_resolved.yaml    # Full resolved configuration
├── system_snapshot.json    # System state at run time
├── latency_samples.csv     # Raw measurements
├── thermal_trace.csv       # Temperature samples
├── frequency_trace.csv     # Frequency samples
├── summary.json            # Statistical summary
├── manifest.json           # Reproducibility manifest
├── warnings.json           # Any warnings
└── figures/                # Generated plots
```

### Key Output Files

**summary.json**:
```json
{
  "success": true,
  "total_inferences": 500,
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

## Extension Points

### Adding a New Runtime

1. Create class implementing `RuntimeInterface` in `inference/runtime_interface.py`
2. Add to `get_runtime()` factory function
3. Update `list_available_runtimes()`

### Adding New Metrics

1. Add computation in `core/statistics.py`
2. Include in runner's `_generate_summary()`
3. Update analysis modules as needed

### Adding New Analysis

1. Create module in `analysis/`
2. Export from `analysis/__init__.py`
3. Add CLI command if needed
