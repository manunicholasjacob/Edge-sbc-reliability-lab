# Contributing to Edge SBC Reliability Lab

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a virtual environment and install dependencies
4. Create a feature branch

```bash
git clone https://github.com/yourusername/edge-sbc-reliability-lab.git
cd edge-sbc-reliability-lab
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
git checkout -b feature/your-feature-name
```

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and reasonably sized

### Documentation

- Update docstrings when changing function behavior
- Update relevant markdown docs for significant changes
- Include examples in docstrings where helpful

### Testing

- Add tests for new functionality
- Ensure existing tests pass before submitting
- Test on Raspberry Pi 5 when possible

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=edge_sbc_reliability_lab tests/
```

## Pull Request Process

1. Update documentation as needed
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md if applicable
5. Submit PR with clear description

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
How was this tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code follows style guidelines
```

## Reporting Issues

When reporting issues, please include:

- Raspberry Pi model and OS version
- Python version
- Relevant package versions
- Steps to reproduce
- Expected vs actual behavior
- Error messages or logs

## Feature Requests

Feature requests are welcome! Please:

- Check existing issues first
- Describe the use case
- Explain why it would be valuable
- Consider implementation approach

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## Questions?

Open an issue with the "question" label or reach out to maintainers.
