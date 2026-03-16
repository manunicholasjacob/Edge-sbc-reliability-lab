# Security Policy

## Reporting Security Issues

If you discover a security vulnerability in Edge SBC Reliability Lab, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email the maintainer directly at: manunicholasjacob@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Security Considerations

This framework is designed for benchmarking and research purposes. When using it:

- **Model files**: Only load models from trusted sources
- **External traces**: Validate CSV files before importing
- **System access**: The framework requires access to system telemetry (temperature, frequency)
- **Execution**: Benchmarks consume significant CPU resources
- **Data privacy**: Results may contain system information; review before sharing

## Best Practices

1. Run benchmarks in isolated environments when possible
2. Verify model file integrity before loading
3. Review configuration files for unexpected commands
4. Keep dependencies updated
5. Use virtual environments to isolate installations
