# Benchmarking Methodology

This document describes the benchmarking methodology used by Edge SBC Reliability Lab.

## Measurement Principles

### Timing Precision

All latency measurements use **monotonic nanosecond timestamps** (`time.monotonic_ns()`) to ensure:
- Immunity to system clock adjustments
- Nanosecond precision
- Consistent measurement across runs

### Warmup Phase

Every benchmark includes a warmup phase to:
- Allow JIT compilation to complete
- Stabilize memory allocations
- Reach initial thermal equilibrium
- Eliminate cold-start artifacts

**Default**: 10-20 warmup iterations (not included in measurements)

### Measurement Modes

#### Burst Mode
- Fixed number of iterations
- No inter-inference delay
- Measures peak throughput capability
- Best for: Quick performance snapshots

#### Sustained Mode
- Duration-based (e.g., 10 minutes)
- Continuous inference load
- Captures thermal drift effects
- Best for: Reliability assessment, thermal analysis

## Statistical Analysis

### Latency Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| Mean | Average latency | General performance |
| Median (P50) | Middle value | Typical experience |
| P90 | 90th percentile | Most users' experience |
| P95 | 95th percentile | Near-worst case |
| P99 | 99th percentile | Tail latency |
| Std Dev | Variability | Consistency assessment |
| CV | Coefficient of variation | Normalized variability |

### Drift Metrics

For sustained benchmarks, we compute:

- **Early vs Late Mean**: Compare first N samples to last N samples
- **Drift Percentage**: `(late_mean - early_mean) / early_mean * 100`
- **Trend Slope**: Linear regression of latency over time

### Stability Score

A composite score (0-100) combining:
- Latency variability (CV)
- Drift magnitude
- Thermal impact
- Outlier frequency

Higher scores indicate more stable, predictable performance.

## Thermal Monitoring

### Temperature Sampling

- **Source**: `/sys/class/thermal/thermal_zone0/temp`
- **Default interval**: 1 second
- **Resolution**: 0.001°C (millidegree readings)

### Frequency Monitoring

- **Source**: `/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq`
- **Purpose**: Detect throttling via frequency reduction

### Throttling Detection

Uses `vcgencmd get_throttled` to detect:
- Under-voltage (power supply issues)
- ARM frequency capping
- Thermal throttling
- Soft temperature limit

## Reproducibility Requirements

### Pre-Run Conditions

For reproducible results, ensure:

1. **CPU Governor**: Set to `performance`
   ```bash
   sudo cpufreq-set -g performance
   ```

2. **Starting Temperature**: Below 50°C
   - Wait for cooldown between runs
   - Use consistent ambient conditions

3. **Background Load**: Minimal (<10% CPU)
   - Close unnecessary applications
   - Disable automatic updates

4. **Power Supply**: Stable 5V/5A
   - Use official Raspberry Pi power supply
   - Avoid USB hubs or underpowered supplies

### Environment Documentation

Each run captures:
- Hardware model and revision
- OS version and kernel
- Python version and packages
- CPU governor state
- Starting temperature
- Git commit (if in repo)

## Fair Comparison Guidelines

### Comparing Runs

For valid comparisons, runs should have:
- Same model file (verified by hash)
- Same batch size and thread count
- Same runtime version
- Similar starting temperature (±5°C)
- Same CPU governor setting

### Fairness Checker

Use the built-in fairness checker:
```python
from edge_sbc_reliability_lab.analysis.fairness_checker import check_fairness

result = check_fairness(["run1", "run2"])
if not result["comparable"]:
    print("Warning:", result["message"])
```

## Power Estimation

### Proxy-Based Approach

**Important**: This framework uses a **proxy-based power estimation**, not actual power measurement.

The model estimates power from:
- CPU utilization percentage
- CPU frequency
- Baseline idle power (~2.5W for Pi 5)
- Maximum load power (~8W for Pi 5)

### Limitations

- Estimates are approximate (±20% error expected)
- Does not account for peripheral power
- Memory and I/O power not modeled
- Use external instrumentation for accurate measurements

### External Power Traces

For accurate power data, import external measurements:
```python
from edge_sbc_reliability_lab.power import load_external_power_trace

trace = load_external_power_trace("power_meter_log.csv")
```

## Benchmark Duration Guidelines

| Test Type | Duration | Purpose |
|-----------|----------|---------|
| Quick test | 30-60s | Sanity check |
| Burst benchmark | 1-2 min | Performance snapshot |
| Short sustained | 5 min | Initial thermal response |
| Standard sustained | 10 min | Thermal drift detection |
| Long sustained | 20-30 min | Full thermal equilibrium |
| Stress test | 60+ min | Long-term reliability |

### Default Suite Runtime

The standard benchmark pack runs approximately **45-75 minutes**, including:
- Multiple burst benchmarks
- Sustained tests at various durations
- Cooldown periods between runs

## Result Interpretation

### Good Results Indicators

- Low CV (<0.1)
- Small drift (<5%)
- Temperature rise <15°C
- No throttling events
- Stability score >80

### Warning Signs

- High CV (>0.2)
- Significant drift (>10%)
- Temperature exceeding 80°C
- Throttling detected
- Stability score <50

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| High variability | Background processes | Close applications |
| Increasing latency | Thermal throttling | Improve cooling |
| Sudden spikes | Frequency scaling | Set governor to performance |
| Inconsistent results | Under-voltage | Check power supply |
