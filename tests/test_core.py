"""Tests for core module functionality."""

import tempfile
from pathlib import Path

import pytest

from edge_sbc_reliability_lab.core.config import ExperimentConfig, load_config
from edge_sbc_reliability_lab.core.statistics import (
    compute_latency_stats,
    compute_drift_metrics,
    compute_stability_score,
)
from edge_sbc_reliability_lab.core.timestamps import TimestampManager, format_duration
from edge_sbc_reliability_lab.core.output import OutputManager


class TestExperimentConfig:
    """Tests for ExperimentConfig."""
    
    def test_default_config(self):
        """Test creating config with defaults."""
        config = ExperimentConfig(
            experiment_name="test",
            model_name="test_model",
            model_path="model.onnx",
            runtime="onnx",
        )
        
        assert config.experiment_name == "test"
        assert config.warmup_runs == 10
        assert config.measured_runs == 100
        assert config.threads == 4
    
    def test_config_save_load(self):
        """Test saving and loading config."""
        config = ExperimentConfig(
            experiment_name="test",
            model_name="test_model",
            model_path="model.onnx",
            runtime="onnx",
            warmup_runs=20,
            measured_runs=500,
        )
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config.save(f.name)
            loaded = load_config(f.name)
        
        assert loaded.experiment_name == config.experiment_name
        assert loaded.warmup_runs == config.warmup_runs
        assert loaded.measured_runs == config.measured_runs
    
    def test_config_validation(self):
        """Test config validation."""
        config = ExperimentConfig(
            experiment_name="test",
            model_name="test_model",
            model_path="model.onnx",
            runtime="onnx",
        )
        
        errors = config.validate()
        # Model path doesn't exist, should have error
        assert len(errors) > 0


class TestStatistics:
    """Tests for statistics functions."""
    
    def test_compute_latency_stats(self):
        """Test latency statistics computation."""
        # Create sample latencies (in nanoseconds)
        latencies_ns = [10_000_000] * 100  # 10ms each
        
        stats = compute_latency_stats(latencies_ns)
        
        assert stats.count == 100
        assert abs(stats.mean_ms - 10.0) < 0.001
        assert abs(stats.median_ms - 10.0) < 0.001
        assert stats.std_ms < 0.001  # No variance
    
    def test_compute_latency_stats_with_variance(self):
        """Test latency stats with variance."""
        # Create latencies with variance
        latencies_ns = [10_000_000 + i * 100_000 for i in range(100)]
        
        stats = compute_latency_stats(latencies_ns)
        
        assert stats.count == 100
        assert stats.min_ms < stats.mean_ms < stats.max_ms
        assert stats.p50_ms <= stats.p90_ms <= stats.p99_ms
    
    def test_compute_drift_metrics(self):
        """Test drift metrics computation."""
        # Create latencies with drift
        latencies_ns = [10_000_000 + i * 10_000 for i in range(100)]
        timestamps_ns = [i * 100_000_000 for i in range(100)]
        
        drift = compute_drift_metrics(latencies_ns, timestamps_ns)
        
        assert "drift_pct" in drift
        assert "early_mean_ms" in drift
        assert "late_mean_ms" in drift
        assert drift["late_mean_ms"] > drift["early_mean_ms"]
    
    def test_stability_score(self):
        """Test stability score computation."""
        # Create stable latencies
        latencies_ns = [10_000_000] * 100
        stats = compute_latency_stats(latencies_ns)
        drift = {"drift_pct": 0, "trend_slope": 0}
        
        score = compute_stability_score(stats, drift)
        
        assert 0 <= score <= 100
        assert score > 80  # Should be high for stable data


class TestTimestampManager:
    """Tests for TimestampManager."""
    
    def test_timestamp_manager(self):
        """Test timestamp manager functionality."""
        tm = TimestampManager()
        
        assert tm.start_time_ns > 0
        assert tm.start_time_iso is not None
        
        elapsed = tm.elapsed_ns()
        assert elapsed >= 0
    
    def test_format_duration(self):
        """Test duration formatting."""
        assert format_duration(0) == "0.0s"
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(3661) == "1h 1m 1s"


class TestOutputManager:
    """Tests for OutputManager."""
    
    def test_create_run_directory(self):
        """Test run directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            om = OutputManager(tmpdir)
            
            paths = om.create_run_directory(
                experiment_name="test",
                model_name="model",
                runtime="onnx",
            )
            
            assert paths.run_dir.exists()
            assert paths.figures_dir.exists()
    
    def test_save_json(self):
        """Test JSON saving."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            data = {"key": "value", "number": 42}
            
            OutputManager.save_json(data, path)
            loaded = OutputManager.load_json(path)
            
            assert loaded == data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
