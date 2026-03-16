# Thermal Measurement Methodology

This document explains the thermal monitoring and drift analysis approach used in Edge SBC Reliability Lab.

## Why Thermal Behavior Matters

On single-board computers like Raspberry Pi 5, thermal conditions significantly impact inference performance:

- **Thermal throttling** reduces CPU frequency when temperature exceeds thresholds
- **Latency drift** occurs as the device heats up during sustained workloads
- **Reproducibility** requires consistent thermal starting conditions
- **Real-world deployment** involves continuous operation, not just burst tests

Most benchmark tools ignore thermal effects. This framework treats thermal behavior as a first-class measurement concern.

## Temperature Monitoring

### Data Sources

The framework reads temperature from Linux sysfs:

```
/sys/class/thermal/thermal_zone0/temp
```

This provides the SoC temperature in millidegrees Celsius.

### Sampling

- **Default interval**: 1 second
- **Configurable**: 0.1s to 10s
- **Background thread**: Non-blocking collection
- **Timestamp alignment**: Synchronized with latency measurements

### Output Format

```csv
timestamp_ns,temp_c
1710600000000000000,45.2
1710600001000000000,45.8
1710600002000000000,46.3
```

## Frequency Monitoring

CPU frequency is monitored alongside temperature:

```
/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

This helps detect throttling events where frequency drops.

## Throttling Detection

On Raspberry Pi, `vcgencmd get_throttled` provides throttling status:

| Bit | Meaning |
|-----|---------|
| 0 | Under-voltage detected |
| 1 | ARM frequency capped |
| 2 | Currently throttled |
| 3 | Soft temperature limit active |
| 16 | Under-voltage has occurred |
| 17 | ARM frequency capping has occurred |
| 18 | Throttling has occurred |
| 19 | Soft temperature limit has occurred |

The framework logs throttling events and includes them in results.

## Thermal Drift Analysis

### Metrics Computed

| Metric | Description |
|--------|-------------|
| Start Temperature | Temperature at benchmark start |
| End Temperature | Temperature at benchmark end |
| Temperature Rise | End - Start temperature |
| Time to Stable | Time until temperature stabilizes |
| Latency-Temperature Correlation | Pearson correlation coefficient |
| Drift Percentage | Latency change from early to late run |

### Early vs Late Comparison

For sustained benchmarks, we compare:
- **Early samples**: First 10% of measurements
- **Late samples**: Last 10% of measurements

```
Drift % = (Late Mean - Early Mean) / Early Mean × 100
```

### Correlation Analysis

We compute Pearson correlation between latency and temperature:

- **r > 0.7**: Strong positive correlation (latency increases with temp)
- **r ≈ 0**: No correlation
- **r < -0.3**: Inverse correlation (unusual, may indicate other factors)

## Thermal Impact Score

A composite score (0-100) indicating thermal stability:

```
Score = 100 - (temp_penalty + drift_penalty + correlation_penalty)
```

Higher scores indicate better thermal stability.

## Best Practices

### Before Benchmarking

1. **Cool start**: Wait until temperature < 50°C
2. **Consistent ambient**: Note room temperature
3. **Cooling setup**: Document heatsink/fan configuration
4. **Idle period**: Let system idle for 2-3 minutes before starting

### During Benchmarking

1. **Monitor temperature**: Watch for throttling
2. **Sustained tests**: Run long enough to reach thermal equilibrium
3. **Multiple runs**: Account for thermal variability

### For Fair Comparisons

1. **Same starting temperature**: ±5°C tolerance
2. **Same cooling setup**: Document any changes
3. **Same ambient conditions**: Note significant differences
4. **Use fairness checker**: Validates comparability

## Configuration

```yaml
# Thermal settings
collect_temperature: true
collect_frequency: true
thermal_sample_interval_sec: 1.0

# Notes for reproducibility
cooling_setup_note: "Official Raspberry Pi active cooler"
ambient_note: "Room temperature ~22°C"
```

## Interpreting Results

### Healthy Thermal Behavior
```json
{
  "thermal": {
    "start_c": 42.0,
    "end_c": 55.0,
    "rise_c": 13.0,
    "throttle_detected": false
  },
  "drift": {
    "drift_pct": 2.5,
    "correlation": 0.45
  }
}
```

### Concerning Thermal Behavior
```json
{
  "thermal": {
    "start_c": 65.0,
    "end_c": 82.0,
    "rise_c": 17.0,
    "throttle_detected": true
  },
  "drift": {
    "drift_pct": 15.2,
    "correlation": 0.89
  }
}
```

## Recommendations

| Temperature | Status | Action |
|-------------|--------|--------|
| < 50°C | Good | Proceed with benchmark |
| 50-65°C | Acceptable | Monitor during run |
| 65-80°C | Warning | Consider better cooling |
| > 80°C | Critical | Throttling likely, improve cooling |

## Limitations

1. **Single sensor**: Only SoC temperature, not individual components
2. **Sampling rate**: May miss rapid transients
3. **External factors**: Ambient temperature affects results
4. **Cooling variability**: Different setups produce different results

## References

- Raspberry Pi thermal management documentation
- Linux thermal subsystem documentation
- SBC thermal characterization literature
