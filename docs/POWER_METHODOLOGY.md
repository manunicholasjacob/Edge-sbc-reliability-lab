# Power Measurement Methodology

This document explains the power measurement approach used in Edge SBC Reliability Lab.

## Overview

Power measurement on single-board computers presents unique challenges. Unlike server-class hardware with built-in power telemetry, Raspberry Pi 5 lacks native power monitoring. This framework provides a layered approach to power estimation.

## Power Measurement Layers

### Layer 1: Software-Based Power Proxy (Default)

The default power estimation uses CPU telemetry as a proxy:

```
Estimated Power = Idle Power + (Load Factor × Dynamic Power Range)
```

**Inputs:**
- CPU utilization percentage
- CPU frequency
- CPU temperature
- Baseline idle power (configurable, default ~2.5W for Pi 5)
- Maximum load power (configurable, default ~8W for Pi 5)

**Limitations:**
- Estimates only, not actual measurements
- Does not account for peripheral power draw
- Memory and I/O power not modeled
- Accuracy varies with workload type
- Expected error: ±20-30%

**When to use:**
- Quick relative comparisons
- Trend analysis over time
- When external instrumentation unavailable

### Layer 2: External Power Trace Import

For accurate measurements, import traces from external instrumentation:

```python
from edge_sbc_reliability_lab.power import load_external_power_trace

trace = load_external_power_trace(
    "power_meter_log.csv",
    timestamp_col="time",
    power_col="watts"
)
```

**Supported formats:**
- CSV with timestamp and power columns
- Configurable column names
- Automatic timestamp alignment

**Recommended instruments:**
- USB power meters (e.g., Ruideng UM25C)
- Smart plugs with power monitoring
- Lab power supplies with logging
- INA219-based measurement boards

### Layer 3: Sensor Adapters (Future)

The architecture supports future sensor integration:

```python
# Future API (not yet implemented)
from edge_sbc_reliability_lab.power.sensors import INA219Adapter

sensor = INA219Adapter(i2c_address=0x40)
power_logger = PowerLogger(sensor)
```

## Energy Metrics

When power data is available, the framework computes:

| Metric | Description |
|--------|-------------|
| Average Power (W) | Mean power during benchmark |
| Total Energy (J) | Joules consumed during run |
| Energy per Inference (mJ) | Joules per inference iteration |
| Efficiency (inf/J) | Inferences per joule |
| Battery Runtime (h) | Estimated runtime on battery |

## Configuration

Power settings in experiment config:

```yaml
# Power proxy settings
collect_power_proxy: true
idle_power_watts: 2.5
max_power_watts: 8.0

# External trace import
external_power_trace_path: "traces/power_log.csv"
power_trace_timestamp_col: "timestamp"
power_trace_power_col: "power_w"
```

## Best Practices

### For Proxy-Based Estimation
1. Use consistent baseline measurements
2. Compare relative values, not absolutes
3. Document estimation method in results
4. Note that estimates are approximate

### For External Measurement
1. Synchronize clocks between Pi and meter
2. Use high sampling rate (≥1 Hz)
3. Include pre/post idle periods
4. Verify trace alignment with benchmark timestamps

### For Publication
1. Clearly state measurement method
2. Report uncertainty bounds
3. Prefer external measurement for energy claims
4. Use proxy only for relative comparisons

## Interpreting Results

### Power Proxy Output
```json
{
  "power_proxy": {
    "method": "cpu_utilization_model",
    "estimated_avg_watts": 5.2,
    "estimated_total_joules": 312.0,
    "confidence": "low",
    "note": "Proxy estimate - use external measurement for accuracy"
  }
}
```

### External Trace Output
```json
{
  "power_measured": {
    "method": "external_trace",
    "source": "usb_power_meter.csv",
    "avg_watts": 5.8,
    "total_joules": 348.0,
    "joules_per_inference": 0.348,
    "confidence": "high"
  }
}
```

## Limitations

1. **No native Pi 5 power monitoring**: Hardware limitation
2. **Proxy accuracy**: Software estimates have significant error
3. **Peripheral power**: USB devices, displays not captured
4. **Transient behavior**: Fast power spikes may be missed
5. **Calibration**: Proxy model may need tuning for specific setups

## References

- Raspberry Pi 5 power consumption specifications
- CPU power modeling literature
- Edge device power measurement best practices
