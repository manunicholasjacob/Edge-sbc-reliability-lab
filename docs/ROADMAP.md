# Roadmap

This document outlines planned future development for Edge SBC Reliability Lab.

## Current Status (v1.0)

### Implemented
- ✅ ONNX Runtime benchmarking
- ✅ TensorFlow Lite support
- ✅ PyTorch support
- ✅ Thermal drift analysis
- ✅ Sustained workload testing
- ✅ CPU utilization-based power proxy
- ✅ External power trace import
- ✅ Config-driven experiments
- ✅ Reproducibility manifests
- ✅ Fairness checker
- ✅ Pre-run health check
- ✅ Leaderboard generation
- ✅ CLI interface

### Validated Platform
- ✅ Raspberry Pi 5 (primary reference)

## Short-Term (v1.1)

### Platform Expansion
- [ ] Raspberry Pi 4 validation
- [ ] Raspberry Pi Zero 2 W testing
- [ ] Orange Pi 5 exploration

### Runtime Enhancements
- [ ] TFLite XNNPACK delegate optimization
- [ ] ONNX Runtime execution providers
- [ ] Quantized model benchmarking

### Analysis Improvements
- [ ] Interactive HTML reports
- [ ] Jupyter notebook templates
- [ ] Automated anomaly detection

## Medium-Term (v1.2)

### Hardware Integration
- [ ] INA219 power sensor adapter
- [ ] USB power meter integration
- [ ] External temperature sensor support

### Advanced Workloads
- [ ] Multi-model concurrent inference
- [ ] Memory pressure testing
- [ ] I/O-bound workload simulation

### Visualization
- [ ] Real-time monitoring dashboard
- [ ] Comparative visualization tools
- [ ] Publication-ready figure templates

## Long-Term (v2.0)

### Platform Expansion
- [ ] NVIDIA Jetson Nano/Orin support
- [ ] BeagleBone AI-64
- [ ] Generic ARM64 Linux support

### Advanced Features
- [ ] Automated regression detection
- [ ] CI/CD integration helpers
- [ ] Cloud result aggregation
- [ ] Model zoo integration

### Research Tools
- [ ] Statistical significance testing
- [ ] Automated paper figure generation
- [ ] BibTeX result export

## Contributing

We welcome contributions! See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines.

Priority areas for contributions:
1. Platform validation on new SBCs
2. Runtime delegate optimizations
3. Power sensor integrations
4. Documentation improvements
