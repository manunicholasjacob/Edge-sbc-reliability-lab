# Changelog

All notable changes to Edge SBC Reliability Lab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-03-16

### Added

- **Core Framework**
  - Experiment configuration system with YAML support
  - Benchmark runner with progress reporting
  - Comprehensive latency statistics (mean, median, percentiles, CV)
  - Drift metrics for sustained workloads
  - Stability scoring system

- **Inference Support**
  - ONNX Runtime integration (primary)
  - TensorFlow Lite support
  - PyTorch support
  - Unified runtime interface for easy extension

- **Thermal Monitoring**
  - Real-time CPU temperature logging
  - CPU frequency tracking
  - Throttling detection via vcgencmd
  - Thermal drift analysis and correlation

- **Platform Detection**
  - Raspberry Pi 5 detection and metadata
  - System snapshot capture
  - CPU governor validation
  - Environment capture for reproducibility

- **Power Estimation**
  - CPU utilization-based power proxy
  - External power meter trace import
  - Energy metrics computation

- **Workload Modes**
  - Burst benchmarks (fixed iterations)
  - Sustained benchmarks (duration-based)
  - Mixed load testing with background stress

- **Analysis Tools**
  - Result summarization
  - Runtime comparison
  - Latency vs temperature analysis
  - Sustained drift analysis
  - Reliability scoring
  - Fairness checker for valid comparisons
  - Leaderboard generation

- **Reproducibility**
  - Environment validation
  - Manifest generation and verification
  - Pre-run health checks
  - Full benchmark suite orchestration

- **CLI**
  - `sbc-bench run` - Run benchmarks
  - `sbc-bench analyze` - Analyze results
  - `sbc-bench compare` - Compare runs
  - `sbc-bench health-check` - System validation
  - `sbc-bench info` - System information
  - `sbc-bench pack` - Run benchmark packs

- **Documentation**
  - Comprehensive README
  - Architecture documentation
  - Methodology guide
  - Quick start guide
  - Contributing guidelines

### Notes

- Designed for Raspberry Pi 5 as reference platform
- Power estimation is proxy-based (not actual measurement)
- Default benchmark suite runs 45-75 minutes
